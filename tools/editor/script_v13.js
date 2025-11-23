const canvas = document.getElementById('editor-canvas');
const ctx = canvas.getContext('2d');
const container = document.querySelector('.canvas-container');

// State
let layout = {
    name: "New Building",
    dimensions: { width: 60, depth: 40, height: 21 },
    floors: []
};

let currentFloorIndex = 0;
let currentTool = 'select'; // select, wall, room
let zoom = 1;
let pan = { x: 50, y: 50 };
let isDragging = false;
let isDraggingLabel = false;
let draggedLabel = null; // {roomIndex: int, offset: {x, y}}
let lastMouse = { x: 0, y: 0 };
let gridSize = 1.0; // meters

// Drawing State
let drawingWall = null; // {start: {x,y}, end: {x,y}}
let selectedObject = null; // {type: 'wall'|'room', floor: idx, room: idx, wall: idx}

// Constants
const PIXELS_PER_METER = 20;

// Initialization
function init() {
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    loadLayout();
    setupEvents();
    requestAnimationFrame(draw);
}

window.onerror = function (msg, url, line, col, error) {
    const status = document.getElementById('status-msg');
    if (status) {
        status.innerText = `Error: ${msg}`;
        status.style.color = 'red';
    }
    console.error(msg, url, line, col, error);
    return false;
};

function resizeCanvas() {
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
    draw();
}

async function loadLayout() {
    try {
        const res = await fetch('/api/layout');
        const data = await res.json();
        if (data.floors) {
            layout = data;
            updateFloorList();
            updateStatus("Layout loaded");
        } else {
            addDefaultFloor();
        }
        fetchLayoutList(); // Refresh list
    } catch (e) {
        console.error(e);
        updateStatus("Error loading layout");
        addDefaultFloor();
    }
}

function addDefaultFloor() {
    layout.floors.push({
        level: 0,
        height: 3.0,
        rooms: []
    });
    updateFloorList();
}

async function fetchLayoutList(selectedToKeep) {
    try {
        const res = await fetch('/api/layouts');
        const files = await res.json();
        const select = document.getElementById('layout-select');
        select.innerHTML = '';
        files.forEach(f => {
            const opt = document.createElement('option');
            opt.value = f;
            opt.innerText = f.replace('.json', '');
            select.appendChild(opt);
        });

        if (selectedToKeep) {
            select.value = selectedToKeep;
        }
    } catch (e) {
        console.error(e);
    }
}

async function saveLayout() {
    try {
        updateStatus("Saving...");
        const select = document.getElementById('layout-select');
        const filename = select.value;

        if (!filename) {
            saveLayoutAs(); // Fallback if no file selected
            return;
        }

        // Ensure internal name matches filename
        layout.name = filename.replace('.json', '');

        const res = await fetch('/api/save_as', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filename: filename,
                data: layout
            })
        });
        const data = await res.json();
        updateStatus(data.message);
        fetchLayoutList(filename);
    } catch (e) {
        console.error(e);
        updateStatus("Error saving layout");
    }
}

let modalCallback = null;
let deleteCallback = null;

function showModal(title, placeholder, initialValue, callback) {
    const modal = document.getElementById('custom-modal');
    const titleEl = document.getElementById('modal-title');
    const input = document.getElementById('modal-input');
    const okBtn = document.getElementById('btn-modal-ok');

    titleEl.innerText = title;
    input.placeholder = placeholder;
    input.value = initialValue || '';
    okBtn.innerText = "Create"; // Default
    if (title.includes("Rename")) okBtn.innerText = "Rename";
    if (title.includes("Save")) okBtn.innerText = "Save";

    modalCallback = callback;

    modal.classList.remove('hidden');
    modal.style.display = 'flex';
    input.focus();
    input.select();

    input.onkeydown = (e) => {
        if (e.key === 'Enter') confirmModal();
        if (e.key === 'Escape') closeModal();
    };
}

function showConfirm(title, message, callback) {
    const modal = document.getElementById('delete-modal');
    const msgEl = document.getElementById('delete-message');

    msgEl.innerText = message;
    deleteCallback = callback;

    modal.classList.remove('hidden');
    modal.style.display = 'flex';
}

function closeModal() {
    const modal = document.getElementById('custom-modal');
    modal.classList.add('hidden');
    modal.style.display = 'none';
    modalCallback = null;
}

function closeDeleteModal() {
    const modal = document.getElementById('delete-modal');
    modal.classList.add('hidden');
    modal.style.display = 'none';
    deleteCallback = null;
}

function confirmModal() {
    const input = document.getElementById('modal-input');
    const val = input.value;

    try {
        if (modalCallback) {
            modalCallback(val);
        }
    } catch (e) {
        console.error("Error in modal callback:", e);
        alert("Error: " + e.message);
    } finally {
        closeModal();
    }
}

function confirmDelete() {
    try {
        if (deleteCallback) {
            deleteCallback();
        }
    } catch (e) {
        console.error("Error in delete callback:", e);
    } finally {
        closeDeleteModal();
    }
}

function createNewRoom() {
    const floor = layout.floors[currentFloorIndex];
    showModal("New Room Label", "Enter room name", `Room ${floor.rooms.length + 1}`, (name) => {
        if (!name) return;
        // Place at center of screen
        const centerWorld = screenToWorld(canvas.width / 2, canvas.height / 2);

        floor.rooms.push({
            name: name,
            walls: [],
            label_pos: [centerWorld.x, centerWorld.y]
        });
        updateStatus(`Created label: ${name}. Drag to move.`);
        draw();
    });
}

function saveLayoutAs() {
    showModal("Save Layout As", "Enter new filename", layout.name, async (filename) => {
        if (!filename) return;
        layout.name = filename; // Update internal name
        try {
            updateStatus("Saving as...");
            const res = await fetch('/api/save_as', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filename: filename,
                    data: layout
                })
            });
            const data = await res.json();
            updateStatus(data.message);

            // Add .json if missing for selection
            let fileToSelect = filename;
            if (!fileToSelect.endsWith('.json')) fileToSelect += '.json';

            fetchLayoutList(fileToSelect);
        } catch (e) {
            console.error(e);
            updateStatus("Error saving layout");
        }
    });
}

async function loadSelectedLayout() {
    const select = document.getElementById('layout-select');
    const filename = select.value;
    if (!filename) return;

    try {
        updateStatus("Loading...");
        const res = await fetch('/api/load', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: filename })
        });
        const data = await res.json();

        if (data.floors) {
            layout = data;
            currentFloorIndex = 0;
            selectedObject = null;
            updateFloorList();
            draw();
            updateStatus("Layout loaded: " + filename);
        } else {
            updateStatus("Invalid layout file");
        }
    } catch (e) {
        console.error(e);
        updateStatus("Error loading layout");
    }
}

async function renameSelectedLayout() {
    const select = document.getElementById('layout-select');
    const oldName = select.value;
    if (!oldName) return;

    showModal("Rename Layout", "Enter new name", oldName.replace('.json', ''), async (newName) => {
        if (!newName) return;
        try {
            const res = await fetch('/api/rename', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    old_filename: oldName,
                    new_filename: newName
                })
            });
            const data = await res.json();
            updateStatus(data.message);
            fetchLayoutList(newName + ".json");
        } catch (e) {
            console.error(e);
            updateStatus("Error renaming file");
        }
    });
}

async function deleteLayout() {
    const select = document.getElementById('layout-select');
    const filename = select.value;
    if (!filename) return;

    showConfirm("Delete Layout", `Are you sure you want to delete "${filename}"? This cannot be undone.`, async () => {
        try {
            const res = await fetch('/api/delete_layout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename: filename })
            });
            const data = await res.json();
            if (res.ok) {
                updateStatus(data.message);
                fetchLayoutList(); // Refresh list
            } else {
                throw new Error(data.message || "Server error");
            }
        } catch (e) {
            console.error(e);
            updateStatus("Error: " + e.message);
        }
    });
}

// Coordinate Conversion
function screenToWorld(sx, sy) {
    return {
        x: (sx - pan.x) / (zoom * PIXELS_PER_METER),
        y: (sy - pan.y) / (zoom * PIXELS_PER_METER)
    };
}

function worldToScreen(wx, wy) {
    return {
        x: wx * zoom * PIXELS_PER_METER + pan.x,
        y: wy * zoom * PIXELS_PER_METER + pan.y
    };
}

function snapToGrid(val) {
    return Math.round(val / gridSize) * gridSize;
}

// Drawing Loop
function draw() {
    ctx.fillStyle = '#2e3238'; // Match CSS bg
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    drawGrid();
    drawContent();

    requestAnimationFrame(draw);
}

function drawGrid() {
    const start = screenToWorld(0, 0);
    const end = screenToWorld(canvas.width, canvas.height);

    ctx.strokeStyle = '#3e444c'; // Lighter grid for dark theme
    ctx.lineWidth = 1;

    const startX = Math.floor(start.x / gridSize) * gridSize;
    const endX = Math.ceil(end.x / gridSize) * gridSize;
    const startY = Math.floor(start.y / gridSize) * gridSize;
    const endY = Math.ceil(end.y / gridSize) * gridSize;

    ctx.beginPath();
    for (let x = startX; x <= endX; x += gridSize) {
        const s = worldToScreen(x, 0);
        ctx.moveTo(s.x, 0);
        ctx.lineTo(s.x, canvas.height);
    }
    for (let y = startY; y <= endY; y += gridSize) {
        const s = worldToScreen(0, y);
        ctx.moveTo(0, s.y);
        ctx.lineTo(canvas.width, s.y);
    }
    ctx.stroke();

    // Origin
    const origin = worldToScreen(0, 0);
    ctx.strokeStyle = '#555';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(origin.x, 0);
    ctx.lineTo(origin.x, canvas.height);
    ctx.moveTo(0, origin.y);
    ctx.lineTo(canvas.width, origin.y);
    ctx.stroke();
}

function drawContent() {
    const floor = layout.floors[currentFloorIndex];
    if (!floor) return;

    // Draw Rooms/Walls
    floor.rooms.forEach((room, rIdx) => {
        // Draw Walls
        room.walls.forEach((wall, wIdx) => {
            const start = worldToScreen(wall.start[0], wall.start[1]);
            const end = worldToScreen(wall.end[0], wall.end[1]);

            ctx.beginPath();
            ctx.moveTo(start.x, start.y);
            ctx.lineTo(end.x, end.y);

            // Style based on selection
            const isSelected = selectedObject &&
                selectedObject.room === rIdx &&
                selectedObject.wall === wIdx;

            ctx.strokeStyle = isSelected ? '#007acc' : getWallColor(wall.material);
            ctx.lineWidth = isSelected ? 4 : 2;
            ctx.stroke();

            // Draw endpoints
            ctx.fillStyle = '#fff';
            ctx.fillRect(start.x - 2, start.y - 2, 4, 4);
            ctx.fillRect(end.x - 2, end.y - 2, 4, 4);
        });

        // Draw Room Label
        let lx, ly;
        if (room.label_pos) {
            lx = room.label_pos[0];
            ly = room.label_pos[1];
        } else if (room.walls.length > 0) {
            // Fallback to center
            let cx = 0, cy = 0;
            room.walls.forEach(w => {
                cx += w.start[0] + w.end[0];
                cy += w.start[1] + w.end[1];
            });
            cx /= (room.walls.length * 2);
            cy /= (room.walls.length * 2);
            lx = cx;
            ly = cy;
        } else {
            // No walls, no label pos? Skip unless it's a new empty room
            return;
        }

        const s = worldToScreen(lx, ly);

        // Label Box
        ctx.font = 'bold 14px "Segoe UI", sans-serif';
        const textMetrics = ctx.measureText(room.name);
        const padding = 8;
        const boxW = textMetrics.width + padding * 2;
        const boxH = 24;

        // Draw Neumorphic Label Box
        ctx.fillStyle = '#2e3238';

        // Shadow
        ctx.shadowColor = '#1e2024';
        ctx.shadowBlur = 6;
        ctx.shadowOffsetX = 3;
        ctx.shadowOffsetY = 3;
        ctx.fillRect(s.x - boxW / 2, s.y - boxH / 2, boxW, boxH);

        // Light highlight
        ctx.shadowColor = '#3e444c';
        ctx.shadowOffsetX = -2;
        ctx.shadowOffsetY = -2;
        ctx.fillRect(s.x - boxW / 2, s.y - boxH / 2, boxW, boxH);

        // Reset shadow
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 0;

        // Text
        ctx.fillStyle = '#e0e5ec';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(room.name, s.x, s.y);
    });

    // Draw Active Drawing
    if (drawingWall) {
        const start = worldToScreen(drawingWall.start.x, drawingWall.start.y);
        const end = worldToScreen(drawingWall.end.x, drawingWall.end.y);

        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);
        ctx.strokeStyle = '#0f0';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.stroke();
        ctx.setLineDash([]);
    }
}

function getWallColor(material) {
    switch (material) {
        case 'concrete': return '#888';
        case 'brick': return '#a52a2a';
        case 'drywall': return '#eee';
        case 'glass': return '#add8e6';
        default: return '#fff';
    }
}

// Interaction
function setupEvents() {
    console.log("Setting up events...");
    // Tools
    document.getElementById('tool-select').onclick = () => setTool('select');
    document.getElementById('tool-wall').onclick = () => setTool('wall');
    document.getElementById('tool-room').onclick = () => createNewRoom();

    // Canvas
    canvas.addEventListener('mousedown', onMouseDown);
    canvas.addEventListener('mousemove', onMouseMove);
    canvas.addEventListener('mouseup', onMouseUp);
    canvas.addEventListener('dblclick', onDoubleClick);
    canvas.addEventListener('wheel', onWheel);

    // UI
    const btnSave = document.getElementById('btn-save');
    if (btnSave) btnSave.onclick = saveLayout;

    document.getElementById('btn-save-as').onclick = saveLayoutAs;
    document.getElementById('btn-load-layout').onclick = loadSelectedLayout;
    document.getElementById('btn-rename-layout').onclick = renameSelectedLayout;

    const btnDelete = document.getElementById('btn-delete-layout');
    if (btnDelete) btnDelete.onclick = deleteLayout;

    document.getElementById('btn-load').onclick = loadLayout;
    document.getElementById('btn-add-floor').onclick = addFloor;
    document.getElementById('btn-remove-floor').onclick = removeFloor;

    document.getElementById('grid-size').oninput = (e) => {
        gridSize = parseFloat(e.target.value);
        draw();
    };
    document.getElementById('zoom-level').oninput = (e) => {
        zoom = parseFloat(e.target.value);
        draw();
    };

    // Modal
    document.getElementById('btn-modal-cancel').onclick = closeModal;
    document.getElementById('btn-modal-ok').onclick = confirmModal;

    // Delete Modal
    document.getElementById('btn-delete-cancel').onclick = closeDeleteModal;
    document.getElementById('btn-delete-confirm').onclick = confirmDelete;
}

function setTool(tool) {
    currentTool = tool;
    document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(`tool-${tool}`).classList.add('active');
    updateStatus(`Tool: ${tool}`);
}

function onMouseDown(e) {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const world = screenToWorld(mx, my);
    const snapped = { x: snapToGrid(world.x), y: snapToGrid(world.y) };

    if (e.button === 1 || (e.button === 0 && e.altKey)) {
        // Pan
        isDragging = true;
        lastMouse = { x: mx, y: my };
        return;
    }

    if (currentTool === 'wall') {
        if (e.button === 0) {
            drawingWall = { start: snapped, end: snapped };
        }
    } else if (currentTool === 'select') {
        // Check for label hit first (prioritize labels)
        const labelHit = hitTestLabel(world.x, world.y);
        if (labelHit) {
            isDraggingLabel = true;
            draggedLabel = labelHit;
            selectedObject = { type: 'room', floor: currentFloorIndex, room: labelHit.roomIndex };
            updatePropertiesPanel();
            return;
        }

        // Simple hit testing (find closest wall)
        selectObjectAt(world.x, world.y);
    }
}

function onMouseMove(e) {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const world = screenToWorld(mx, my);

    document.getElementById('cursor-coords').innerText = `${world.x.toFixed(1)}, ${world.y.toFixed(1)}`;

    if (isDragging) {
        pan.x += mx - lastMouse.x;
        pan.y += my - lastMouse.y;
        lastMouse = { x: mx, y: my };
        return;
    }

    if (isDraggingLabel && draggedLabel) {
        const floor = layout.floors[currentFloorIndex];
        const room = floor.rooms[draggedLabel.roomIndex];
        room.label_pos = [world.x, world.y];
        return; // Don't do other checks
    }

    if (drawingWall) {
        drawingWall.end = { x: snapToGrid(world.x), y: snapToGrid(world.y) };
    }
}

function onMouseUp(e) {
    if (isDragging) {
        isDragging = false;
        return;
    }

    if (isDraggingLabel) {
        isDraggingLabel = false;
        draggedLabel = null;
        return;
    }

    if (drawingWall) {
        // Finish wall
        const floor = layout.floors[currentFloorIndex];
        if (floor.rooms.length === 0) {
            alert("Please create a room/label first!");
            drawingWall = null;
            return;
        }

        // Add to the last room (or selected room if we had that logic)
        // If a room is selected, add to it. Otherwise add to last.
        let targetRoom = floor.rooms[floor.rooms.length - 1];
        if (selectedObject && selectedObject.type === 'room' && selectedObject.floor === currentFloorIndex) {
            targetRoom = floor.rooms[selectedObject.room];
        }

        // Don't add zero-length walls
        if (drawingWall.start.x !== drawingWall.end.x || drawingWall.start.y !== drawingWall.end.y) {
            targetRoom.walls.push({
                start: [drawingWall.start.x, drawingWall.start.y],
                end: [drawingWall.end.x, drawingWall.end.y],
                material: 'concrete'
            });
        }

        drawingWall = null;
        draw(); // Force redraw
    }
}

function onDoubleClick(e) {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const world = screenToWorld(mx, my);

    const labelHit = hitTestLabel(world.x, world.y);
    if (labelHit) {
        const floor = layout.floors[currentFloorIndex];
        const room = floor.rooms[labelHit.roomIndex];

        showModal("Rename Label", "Enter new name", room.name, (newName) => {
            room.name = newName;
            updatePropertiesPanel();
            draw();
        });
    }
}

function onWheel(e) {
    e.preventDefault();
    const zoomSpeed = 0.1;
    if (e.deltaY < 0) {
        zoom = Math.min(zoom + zoomSpeed, 3);
    } else {
        zoom = Math.max(zoom - zoomSpeed, 0.5);
    }
    document.getElementById('zoom-level').value = zoom;
    draw();
}

function hitTestLabel(wx, wy) {
    const floor = layout.floors[currentFloorIndex];
    // Approximate hit box size in world units
    // 14px font ~ 0.7m height roughly? Let's be generous.
    const hitW = 4.0; // meters
    const hitH = 1.5; // meters

    for (let i = 0; i < floor.rooms.length; i++) {
        const room = floor.rooms[i];
        if (!room.label_pos) continue;

        const lx = room.label_pos[0];
        const ly = room.label_pos[1];

        if (Math.abs(wx - lx) < hitW / 2 && Math.abs(wy - ly) < hitH / 2) {
            return { roomIndex: i };
        }
    }
    return null;
}

function selectObjectAt(wx, wy) {
    const floor = layout.floors[currentFloorIndex];
    const threshold = 0.5 / zoom; // Hit tolerance

    selectedObject = null;
    updatePropertiesPanel();

    for (let r = 0; r < floor.rooms.length; r++) {
        const room = floor.rooms[r];
        for (let w = 0; w < room.walls.length; w++) {
            const wall = room.walls[w];
            // Point to line segment distance
            const dist = pointToSegmentDist(wx, wy, wall.start[0], wall.start[1], wall.end[0], wall.end[1]);
            if (dist < threshold) {
                selectedObject = { type: 'wall', floor: currentFloorIndex, room: r, wall: w };
                updatePropertiesPanel();
                return;
            }
        }
    }
}

function pointToSegmentDist(x, y, x1, y1, x2, y2) {
    const A = x - x1;
    const B = y - y1;
    const C = x2 - x1;
    const D = y2 - y1;

    const dot = A * C + B * D;
    const len_sq = C * C + D * D;
    let param = -1;
    if (len_sq !== 0) param = dot / len_sq;

    let xx, yy;

    if (param < 0) {
        xx = x1;
        yy = y1;
    } else if (param > 1) {
        xx = x2;
        yy = y2;
    } else {
        xx = x1 + param * C;
        yy = y1 + param * D;
    }

    const dx = x - xx;
    const dy = y - yy;
    return Math.sqrt(dx * dx + dy * dy);
}

// UI Updates
function updateFloorList() {
    const list = document.getElementById('floor-list');
    list.innerHTML = '';
    layout.floors.forEach((f, idx) => {
        const div = document.createElement('div');
        div.className = `floor-item ${idx === currentFloorIndex ? 'active' : ''}`;
        div.innerText = `Floor ${f.level} (${f.height}m)`;
        div.onclick = () => {
            currentFloorIndex = idx;
            selectedObject = null;
            updateFloorList();
            updatePropertiesPanel();
            draw();
        };
        list.appendChild(div);
    });
}

function addFloor() {
    const level = layout.floors.length;
    layout.floors.push({
        level: level,
        height: 3.0,
        rooms: []
    });
    currentFloorIndex = layout.floors.length - 1;
    updateFloorList();
    draw();
}

function removeFloor() {
    if (layout.floors.length <= 1) {
        alert("Cannot remove the last floor!");
        return;
    }

    // Remove the current floor
    layout.floors.splice(currentFloorIndex, 1);

    // Adjust levels of remaining floors
    layout.floors.forEach((f, idx) => {
        f.level = idx;
    });

    // Update index
    if (currentFloorIndex >= layout.floors.length) {
        currentFloorIndex = layout.floors.length - 1;
    }

    updateFloorList();
    draw();
}

function updateStatus(msg) {
    const status = document.getElementById('status-msg');
    if (status) {
        status.innerText = msg;
        setTimeout(() => {
            status.innerText = '';
        }, 3000);
    }
}

function updatePropertiesPanel() {
    const panel = document.getElementById('properties-panel');
    if (!selectedObject) {
        // Show Floor Properties
        const floor = layout.floors[currentFloorIndex];
        panel.innerHTML = `
            <div class="prop-row">
                <label>Floor Height (m)</label>
                <input type="number" id="prop-floor-height" value="${floor.height}" step="0.1" min="2.0">
            </div>
            <p class="hint" style="margin-top:10px; font-size:0.8em">Select a wall or label to edit its properties.</p>
        `;

        document.getElementById('prop-floor-height').onchange = (e) => {
            let val = parseFloat(e.target.value);
            if (val < 2.0) val = 2.0; // Minimum height constraint
            floor.height = val;
            updateFloorList(); // Update the list to show new height
        };
        return;
    }

    if (selectedObject.type === 'room') {
        const floor = layout.floors[selectedObject.floor];
        const room = floor.rooms[selectedObject.room];
        panel.innerHTML = `
            <div class="prop-row">
                <label>Label</label>
                <input type="text" id="prop-room-name" value="${room.name}">
            </div>
            <button id="btn-delete-room" class="action-btn small" style="background:#a00">Delete Label & Walls</button>
         `;

        document.getElementById('prop-room-name').onchange = (e) => {
            room.name = e.target.value;
            draw();
        };

        document.getElementById('btn-delete-room').onclick = () => {
            floor.rooms.splice(selectedObject.room, 1);
            selectedObject = null;
            updatePropertiesPanel();
            draw();
        };
        return;
    }

    if (selectedObject.type === 'wall') {
        const floor = layout.floors[selectedObject.floor];
        const room = floor.rooms[selectedObject.room];
        const wall = room.walls[selectedObject.wall];

        panel.innerHTML = `
            <div class="prop-row">
                <label>Room</label>
                <span>${room.name}</span>
            </div>
            <div class="prop-row">
                <label>Material</label>
                <select id="prop-material">
                    <option value="concrete">Concrete</option>
                    <option value="brick">Brick</option>
                    <option value="drywall">Drywall</option>
                    <option value="glass">Glass</option>
                </select>
            </div>
            <button id="btn-delete-wall" class="action-btn small" style="background:#a00">Delete Wall</button>
        `;

        const sel = document.getElementById('prop-material');
        sel.value = wall.material || 'concrete';
        sel.onchange = (e) => {
            wall.material = e.target.value;
            draw();
        };

        document.getElementById('btn-delete-wall').onclick = () => {
            room.walls.splice(selectedObject.wall, 1);
            selectedObject = null;
            updatePropertiesPanel();
            draw();
        };
    }
}

init();
