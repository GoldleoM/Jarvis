// --- Three.js Setup (Glowing Orb) ---
let backendState = 'idle';
let scene, camera, renderer, orb, material, light;
let orbSpeed = 0.005;
let orbScale = 1.0;
let targetScale = 1.0;
let webGLSupported = false;

try {
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(200, 200);
    document.getElementById('canvas-container').appendChild(renderer.domElement);

    const geometry = new THREE.IcosahedronGeometry(1, 3);
    material = new THREE.MeshStandardMaterial({
        color: 0x00ffff,
        emissive: 0x0088ff,
        emissiveIntensity: 0.6,
        wireframe: true,
        transparent: true,
        opacity: 0.8
    });
    orb = new THREE.Mesh(geometry, material);
    scene.add(orb);

    light = new THREE.PointLight(0x00ffff, 3, 100);
    light.position.set(0, 0, 5);
    scene.add(light);

    camera.position.z = 2.5;
    webGLSupported = true;

    function animate() {
        requestAnimationFrame(animate);
        
        orb.rotation.x += orbSpeed;
        orb.rotation.y += orbSpeed;
        
        orbScale += (targetScale - orbScale) * 0.1;
        orb.scale.set(orbScale, orbScale, orbScale);

        if (backendState === 'listening' || backendState === 'speaking') {
            const time = Date.now() * 0.01;
            const pulse = 1.0 + Math.sin(time) * 0.15;
            orb.scale.set(orbScale * pulse, orbScale * pulse, orbScale * pulse);
        }

        renderer.render(scene, camera);
    }
    animate();
} catch (e) {
    console.error("WebGL failed to initialize:", e);
    document.getElementById('status-text').innerText = "WebGL Not Supported";
}

// --- Backend Integration ---
let backend = null;
const statusText = document.getElementById('status-text');
const cancelBtn = document.getElementById('cancel-btn');
const chatInput = document.getElementById('chat-input');
const responseBox = document.getElementById('response-box');

// --- Fade & Typewriter Variables ---
let fadeTimeout = null;
let typewriterInterval = null;

// --- History Logic ---
const chatHistory = [];
const historyBtn = document.getElementById('history-btn');
const historyModal = document.getElementById('history-modal');
const closeHistoryBtn = document.getElementById('close-history-btn');
const historyContent = document.getElementById('history-content');

if (historyBtn) {
    historyBtn.addEventListener('click', () => {
        historyModal.style.display = 'flex';
        renderHistory();
        sendMaskUpdate();
    });
}
if (closeHistoryBtn) {
    closeHistoryBtn.addEventListener('click', () => {
        historyModal.style.display = 'none';
        sendMaskUpdate();
    });
}

function appendToHistory(speaker, text) {
    if (!text) return;
    chatHistory.push({ speaker, text });
    if (historyModal && historyModal.style.display === 'flex') {
        renderHistory();
    }
}

function renderHistory() {
    if (!historyContent) return;
    historyContent.innerHTML = '';
    chatHistory.forEach(entry => {
        const div = document.createElement('div');
        div.className = `chat-bubble ${entry.speaker === 'User' ? 'chat-user' : 'chat-jarvis'}`;
        div.innerText = `${entry.text}`;
        historyContent.appendChild(div);
    });
    historyContent.scrollTop = historyContent.scrollHeight;
}

function sendMaskUpdate() {
    if (!backend) return;
    const rects = [];
    
    if (typeof isDraggingAny !== 'undefined' && isDraggingAny) {
        // Prevent mouse from escaping by locking the whole screen during a drag
        rects.push({x: 0, y: 0, w: window.innerWidth, h: window.innerHeight, shape: 'rect'});
        backend.update_mask(JSON.stringify(rects));
        return;
    }
    
    // Globe mask
    const canvas = document.getElementById('canvas-container').getBoundingClientRect();
    if (canvas.width > 0) {
        rects.push({x: canvas.left - 20, y: canvas.top - 20, w: canvas.width + 40, h: canvas.height + 40, shape: 'ellipse'});
    }
    
    // Chat container
    const chat = document.getElementById('chat-container').getBoundingClientRect();
    if (chat.width > 0) {
        rects.push({x: chat.left - 35, y: chat.top - 35, w: chat.width + 70, h: chat.height + 70, shape: 'rect'});
    }
    
    // Status text
    const status = document.getElementById('status-text').getBoundingClientRect();
    if (status.width > 0) {
        rects.push({x: status.left - 15, y: status.top - 15, w: status.width + 30, h: status.height + 30, shape: 'rect'});
    }

    // Response box
    const rb = document.getElementById('response-box').getBoundingClientRect();
    if (rb.width > 0 && responseBox.style.display !== 'none' && !responseBox.classList.contains('fade-out')) {
        rects.push({x: rb.left - 35, y: rb.top - 35, w: rb.width + 70, h: rb.height + 70, shape: 'rect'});
    }

    // History Modal
    if (historyModal && historyModal.style.display === 'flex') {
        const hm = historyModal.getBoundingClientRect();
        rects.push({x: hm.left - 40, y: hm.top - 40, w: hm.width + 80, h: hm.height + 80, shape: 'rect'});
    }

    backend.update_mask(JSON.stringify(rects));
}

function updateState(newState, text = "") {
    backendState = newState;
    if (webGLSupported) {
        if (newState === 'idle') {
            material.color.setHex(0x00ffff);
            material.emissive.setHex(0x0088ff);
            light.color.setHex(0x00ffff);
            orbSpeed = 0.005;
            targetScale = 1.0;
        } else if (newState === 'listening') {
            material.color.setHex(0x00ffaa);
            material.emissive.setHex(0x00aa55);
            light.color.setHex(0x00ffaa);
            orbSpeed = 0.02;
            targetScale = 1.2;
        } else if (newState === 'thinking') {
            material.color.setHex(0xff00ff);
            material.emissive.setHex(0xaa00aa);
            light.color.setHex(0xff00ff);
            orbSpeed = 0.05;
            targetScale = 1.1;
        } else if (newState === 'speaking') {
            material.color.setHex(0x00aaff);
            material.emissive.setHex(0x0055ff);
            light.color.setHex(0x00aaff);
            orbSpeed = 0.015;
            targetScale = 1.3;
        }
    }
    
    if (newState === 'idle') {
        statusText.innerText = text || "ONLINE";
        cancelBtn.style.display = 'none';
        chatInput.placeholder = "Type a command or say Jarvis...";
    } else if (newState === 'listening') {
        if (text && text.startsWith('"') && text.endsWith('"')) {
            chatInput.value = text.slice(1, -1);
            statusText.innerText = "LISTENING...";
        } else {
            statusText.innerText = text || "LISTENING...";
        }
        cancelBtn.style.display = 'none';
    } else if (newState === 'thinking') {
        if (chatInput.value) {
            appendToHistory('User', chatInput.value);
            chatInput.value = '';
        }
        statusText.innerText = text || "THINKING...";
        cancelBtn.style.display = 'block';
    } else if (newState === 'speaking') {
        statusText.innerText = "SPEAKING...";
        
        // Interrupt fade
        if (fadeTimeout) clearTimeout(fadeTimeout);
        responseBox.classList.remove('fade-out');
        
        appendToHistory('Jarvis', text);
        
        // Typewriter effect
        if (typewriterInterval) clearInterval(typewriterInterval);
        responseBox.innerText = "";
        let i = 0;
        
        if (responseBox.style.display === 'none' || responseBox.style.display === '') {
            responseBox.style.display = 'block';
            
            const maxX = window.innerWidth - 320 - 20; // 320 is max-width
            const maxY = window.innerHeight - 150 - 20; // estimated height
            boxLeft = Math.max(10, Math.floor(Math.random() * maxX));
            boxTop = Math.max(10, Math.floor(Math.random() * maxY));
            responseBox.style.left = boxLeft + 'px';
            responseBox.style.top = boxTop + 'px';
        }
        
        typewriterInterval = setInterval(() => {
            if (i < text.length) {
                responseBox.textContent = text.substring(0, i + 1);
                i++;
                sendMaskUpdate(); // keep mask accurate as text grows
            } else {
                clearInterval(typewriterInterval);
            }
        }, 30);
        
        cancelBtn.style.display = 'block';
    }
    
    if (newState !== 'speaking') {
        if (responseBox.style.display === 'block' && !responseBox.classList.contains('fade-out')) {
            if (fadeTimeout) clearTimeout(fadeTimeout);
            fadeTimeout = setTimeout(() => {
                responseBox.classList.add('fade-out');
                setTimeout(() => {
                    if (responseBox.classList.contains('fade-out')) {
                        responseBox.style.display = 'none';
                        responseBox.classList.remove('fade-out');
                        sendMaskUpdate();
                    }
                }, 500); // Wait for transition
            }, 4000); // Wait 4 seconds
        }
    }
}

function initWebChannel() {
    if (typeof qt !== 'undefined' && qt.webChannelTransport) {
        new QWebChannel(qt.webChannelTransport, function(channel) {
            backend = channel.objects.backend;
            
            backend.stateChanged.connect(function(state, text) {
                updateState(state, text);
            });

            chatInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    const val = chatInput.value.trim();
                    if (val) {
                        backend.receive_input(val);
                        chatInput.value = '';
                    }
                }
            });

            cancelBtn.addEventListener('click', function() {
                backend.cancel_task();
            });
            
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape' && backendState === 'thinking') {
                    backend.cancel_task();
                }
            });
            
            // Initial mask setup once UI is ready
            setTimeout(sendMaskUpdate, 500);
        });
    } else {
        console.log("Waiting for QWebChannel transport...");
        setTimeout(initWebChannel, 100);
    }
}
initWebChannel();

// --- Drag and Drop ---
let isDraggingHud = false;
let isDraggingBox = false;
let isDraggingHistory = false;
let isDraggingAny = false;
let startX, startY;

const hud = document.getElementById('hud-container');
let hudLeft = (window.innerWidth - 480) / 2;
let hudTop = window.innerHeight - 280 - 40;
hud.style.left = hudLeft + 'px';
hud.style.top = hudTop + 'px';

let boxLeft = 0;
let boxTop = 0;

let historyLeft = window.innerWidth / 2;
let historyTop = window.innerHeight / 2;

document.addEventListener('mousedown', (e) => {
    if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'BUTTON') {
        if (historyModal && historyModal.style.display === 'flex' && historyModal.contains(e.target) && !historyContent.contains(e.target)) {
            isDraggingHistory = true;
            startX = e.clientX;
            startY = e.clientY;
            const rect = historyModal.getBoundingClientRect();
            historyLeft = rect.left + rect.width / 2;
            historyTop = rect.top + rect.height / 2;
        } else if (responseBox.contains(e.target)) {
            isDraggingBox = true;
            startX = e.clientX;
            startY = e.clientY;
            boxLeft = parseInt(responseBox.style.left) || 0;
            boxTop = parseInt(responseBox.style.top) || 0;
        } else if (hud.contains(e.target)) {
            isDraggingHud = true;
            startX = e.clientX;
            startY = e.clientY;
        }
        
        isDraggingAny = isDraggingHud || isDraggingBox || isDraggingHistory;
        if (isDraggingAny) sendMaskUpdate();
    }
});

document.addEventListener('mousemove', (e) => {
    if (!isDraggingAny) return;
    
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    
    if (isDraggingHud) {
        hudLeft += dx;
        hudTop += dy;
        hud.style.left = hudLeft + 'px';
        hud.style.top = hudTop + 'px';
    } else if (isDraggingBox) {
        boxLeft += dx;
        boxTop += dy;
        responseBox.style.left = boxLeft + 'px';
        responseBox.style.top = boxTop + 'px';
    } else if (isDraggingHistory) {
        historyLeft += dx;
        historyTop += dy;
        historyModal.style.left = historyLeft + 'px';
        historyModal.style.top = historyTop + 'px';
    }
    
    startX = e.clientX;
    startY = e.clientY;
});

document.addEventListener('mouseup', () => {
    if (isDraggingAny) {
        isDraggingHud = false;
        isDraggingBox = false;
        isDraggingHistory = false;
        isDraggingAny = false;
        sendMaskUpdate();
    }
});
