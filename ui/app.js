// --- Three.js Setup (Glowing Orb) ---
let backendState = 'idle';
let scene, camera, renderer, orb, material, light;
let orbSpeed = 0.001;
let targetOrbSpeed = 0.001;
let orbScale = 1.0;
let targetScale = 1.0;
let targetColor = new THREE.Color(0x00ffff);
let targetEmissive = new THREE.Color(0x0088ff);
let targetLight = new THREE.Color(0x00ffff);
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
        
        orbSpeed += (targetOrbSpeed - orbSpeed) * 0.05;
        orb.rotation.x += orbSpeed;
        orb.rotation.y += orbSpeed;
        
        orbScale += (targetScale - orbScale) * 0.05;
        orb.scale.set(orbScale, orbScale, orbScale);

        // Smoothly interpolate colors
        material.color.lerp(targetColor, 0.05);
        material.emissive.lerp(targetEmissive, 0.05);
        light.color.lerp(targetLight, 0.05);

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

// --- Auto-resize Textarea ---
chatInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = this.scrollHeight + 'px';
    sendMaskUpdate();
});

// --- Fade & Typewriter Variables ---
let fadeTimeout = null;
let typewriterInterval = null;

// --- History Logic ---
const chatHistory = [];
const historyBtn = document.getElementById('history-btn');
const historyModal = document.getElementById('history-modal');
const closeHistoryBtn = document.getElementById('close-history-btn');
const historyContent = document.getElementById('history-content');

const settingsBtn = document.getElementById('settings-btn');
const settingsModal = document.getElementById('settings-modal');
const closeSettingsBtn = document.getElementById('close-settings-btn');
const saveSettingsBtn = document.getElementById('save-settings-btn');

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

if (settingsBtn) {
    settingsBtn.addEventListener('click', () => {
        settingsModal.style.display = 'flex';
        if (backend) {
            backend.get_microphones(function(micsJson) {
                try {
                    const mics = JSON.parse(micsJson);
                    const micOptions = document.getElementById('mic-options');
                    micOptions.innerHTML = '';
                    mics.forEach(mic => {
                        const div = document.createElement('div');
                        div.innerText = mic.index === -1 ? mic.name : `[${mic.index}] ${mic.name}`;
                        div.onclick = function() {
                            document.getElementById('setting-mic-index').value = mic.index;
                            document.getElementById('mic-display').innerText = div.innerText;
                        };
                        micOptions.appendChild(div);
                    });
                    
                    backend.get_settings(function(settingsJson) {
                        try {
                            const s = JSON.parse(settingsJson);
                            document.getElementById('setting-wake-word').value = s.WAKE_WORD || '';
                            
                            const micIndex = s.MIC_INDEX !== null && s.MIC_INDEX !== undefined ? s.MIC_INDEX : -1;
                            document.getElementById('setting-mic-index').value = micIndex;
                            const selectedMic = mics.find(m => m.index === micIndex);
                            document.getElementById('mic-display').innerText = selectedMic ? (selectedMic.index === -1 ? selectedMic.name : `[${selectedMic.index}] ${selectedMic.name}`) : `Unknown (${micIndex})`;
                            
                            document.getElementById('setting-opencode-model').value = s.OPENCODE_MODEL || '';
                            document.getElementById('setting-opencode-provider').value = s.OPENCODE_PROVIDER || '';
                            document.getElementById('setting-whisper-model').value = s.WHISPER_MODEL || 'medium.en';
                            document.getElementById('whisper-display').innerText = s.WHISPER_MODEL || 'medium.en';
                            document.getElementById('setting-compute-type').value = s.WHISPER_COMPUTE_TYPE || 'float16';
                            document.getElementById('compute-display').innerText = s.WHISPER_COMPUTE_TYPE || 'float16';
                            document.getElementById('setting-vad-threshold').value = s.VAD_THRESHOLD || 0.5;
                            document.getElementById('setting-orb-color').value = s.ORB_COLOR || '#00ffff';
                            document.getElementById('setting-orb-glow').value = s.ORB_GLOW || '#0088ff';
                            document.getElementById('setting-ui-shortcut').value = s.UI_SHORTCUT || 'alt+space';
                        } catch(e) { console.error("Error parsing settings:", e); }
                    });
                } catch(e) { console.error("Error loading mics:", e); }
            });
        }
        sendMaskUpdate();
    });
}

if (closeSettingsBtn) {
    closeSettingsBtn.addEventListener('click', () => {
        settingsModal.style.display = 'none';
        sendMaskUpdate();
    });
}

if (saveSettingsBtn) {
    saveSettingsBtn.addEventListener('click', () => {
        const s = {
            WAKE_WORD: document.getElementById('setting-wake-word').value,
            MIC_INDEX: document.getElementById('setting-mic-index').value === '' ? null : parseInt(document.getElementById('setting-mic-index').value),
            OPENCODE_MODEL: document.getElementById('setting-opencode-model').value,
            OPENCODE_PROVIDER: document.getElementById('setting-opencode-provider').value,
            WHISPER_MODEL: document.getElementById('setting-whisper-model').value,
            WHISPER_COMPUTE_TYPE: document.getElementById('setting-compute-type').value || 'float16',
            VAD_THRESHOLD: parseFloat(document.getElementById('setting-vad-threshold').value) || 0.5,
            ORB_COLOR: document.getElementById('setting-orb-color').value || '#00ffff',
            ORB_GLOW: document.getElementById('setting-orb-glow').value || '#0088ff',
            UI_SHORTCUT: document.getElementById('setting-ui-shortcut').value || 'alt+space'
        };
        
        targetColor.setHex(parseInt(s.ORB_COLOR.replace('#', '0x')));
        targetEmissive.setHex(parseInt(s.ORB_GLOW.replace('#', '0x')));
        targetLight.setHex(parseInt(s.ORB_COLOR.replace('#', '0x')));
        
        if (backend) {
            backend.save_settings(JSON.stringify(s));
        }
        
        settingsModal.style.display = 'none';
        sendMaskUpdate();
    });
}

const testMicBtn = document.getElementById('test-mic-btn');
if (testMicBtn) {
    testMicBtn.addEventListener('click', () => {
        let idx = document.getElementById('setting-mic-index').value;
        if (idx === "") idx = -1;
        else idx = parseInt(idx);
        
        const res = document.getElementById('test-mic-result');
        if (res) {
            res.innerText = "Listening for 1.5s...";
            res.style.color = "yellow";
        }
        testMicBtn.disabled = true;
        
        if (backend) {
            backend.test_mic(idx);
        }
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

    // Settings Modal
    if (settingsModal && settingsModal.style.display === 'flex') {
        const sm = settingsModal.getBoundingClientRect();
        rects.push({x: sm.left - 40, y: sm.top - 40, w: sm.width + 80, h: sm.height + 80, shape: 'rect'});
    }

    backend.update_mask(JSON.stringify(rects));
}

function updateState(newState, text = "") {
    backendState = newState;
    if (webGLSupported) {
        if (newState === 'idle') {
            targetColor.setHex(0x00ffff);
            targetEmissive.setHex(0x0088ff);
            targetLight.setHex(0x00ffff);
            targetOrbSpeed = 0.001;
            targetScale = 1.0;
        } else if (newState === 'listening') {
            targetColor.setHex(0x00ffaa);
            targetEmissive.setHex(0x00aa55);
            targetLight.setHex(0x00ffaa);
            targetOrbSpeed = 0.004;
            targetScale = 1.15;
        } else if (newState === 'thinking') {
            targetColor.setHex(0xff00ff);
            targetEmissive.setHex(0xaa00aa);
            targetLight.setHex(0xff00ff);
            targetOrbSpeed = 0.008;
            targetScale = 1.1;
        } else if (newState === 'speaking') {
            targetColor.setHex(0x00aaff);
            targetEmissive.setHex(0x0055ff);
            targetLight.setHex(0x00aaff);
            targetOrbSpeed = 0.003;
            targetScale = 1.2;
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
        if (chatInput.value && chatHistory.length === 0 || (chatHistory.length > 0 && chatHistory[chatHistory.length - 1].text !== chatInput.value)) {
            appendToHistory('User', chatInput.value);
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
                        if (backendState === 'idle') {
                            chatInput.value = '';
                            chatInput.style.height = 'auto';
                        }
                        sendMaskUpdate();
                    }
                }, 500); // Wait for transition
            }, 4000); // Wait 4 seconds
        }
    }
    
    // Always update mask when state changes to account for text width changes
    setTimeout(sendMaskUpdate, 10);
}

function initWebChannel() {
    if (typeof qt !== 'undefined' && qt.webChannelTransport) {
        new QWebChannel(qt.webChannelTransport, function(channel) {
            backend = channel.objects.backend;
            
            backend.stateChanged.connect(function(state, text) {
                updateState(state, text);
            });
            
            backend.micTestCompleted.connect(function(msg) {
                const btn = document.getElementById('test-mic-btn');
                const res = document.getElementById('test-mic-result');
                if (btn) btn.disabled = false;
                if (res) {
                    if (msg.startsWith("Error") || msg.includes("0%")) {
                        res.style.color = "red";
                    } else {
                        res.style.color = "lime";
                    }
                    res.innerText = msg;
                }
            });

            chatInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    const val = chatInput.value.trim();
                    if (val) {
                        backend.receive_input(val);
                        // Do not clear here, wait for response fade out
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
let isDraggingSettings = false;
let isDraggingAny = false;
let startX, startY;

const hud = document.getElementById('hud-container');
let hudLeft = (window.innerWidth - 480) / 2;
let hudTop = window.innerHeight - 280 - 40;
hud.style.left = hudLeft + 'px';
hud.style.top = hudTop + 'px';

let boxLeft = 0;
let boxTop = 0;

let historyLeft = (window.innerWidth / 2) - 300;
let historyTop = (window.innerHeight / 2) - 200;

let settingsLeft = (window.innerWidth / 2) - 350;
let settingsTop = (window.innerHeight / 2) - 250;

document.addEventListener('mousedown', (e) => {
    if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'BUTTON' && e.target.tagName !== 'SELECT' && e.target.tagName !== 'LABEL') {
        if (settingsModal && settingsModal.style.display === 'flex' && settingsModal.contains(e.target)) {
            // Prevent dragging if clicking inside the settings content area
            const contentArea = settingsModal.querySelector('.settings-content');
            if (!contentArea.contains(e.target)) {
                isDraggingSettings = true;
                startX = e.clientX;
                startY = e.clientY;
                const rect = settingsModal.getBoundingClientRect();
                settingsLeft = rect.left;
                settingsTop = rect.top;
            }
        } else if (historyModal && historyModal.style.display === 'flex' && historyModal.contains(e.target) && !historyContent.contains(e.target)) {
            isDraggingHistory = true;
            startX = e.clientX;
            startY = e.clientY;
            const rect = historyModal.getBoundingClientRect();
            historyLeft = rect.left;
            historyTop = rect.top;
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
        
        isDraggingAny = isDraggingHud || isDraggingBox || isDraggingHistory || isDraggingSettings;
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
    } else if (isDraggingSettings) {
        settingsLeft += dx;
        settingsTop += dy;
        settingsModal.style.left = settingsLeft + 'px';
        settingsModal.style.top = settingsTop + 'px';
    }
    
    startX = e.clientX;
    startY = e.clientY;
});

document.addEventListener('mouseup', () => {
    if (isDraggingAny) {
        isDraggingHud = false;
        isDraggingBox = false;
        isDraggingHistory = false;
        isDraggingSettings = false;
        isDraggingAny = false;
        sendMaskUpdate();
    }
});

// Handle resizing of the history modal to update the Python interaction mask
const resizeObserver = new ResizeObserver(() => {
    if (historyModal && historyModal.style.display === 'flex') {
        sendMaskUpdate();
    }
    if (settingsModal && settingsModal.style.display === 'flex') {
        sendMaskUpdate();
    }
});
resizeObserver.observe(historyModal);
resizeObserver.observe(settingsModal);

// Custom Dropdown Click Handlers
document.addEventListener('click', (e) => {
    const isValue = e.target.classList.contains('custom-select-value');
    if (isValue) {
        const options = e.target.nextElementSibling;
        const wasOpen = options.classList.contains('open');
        document.querySelectorAll('.custom-select-options.open').forEach(el => el.classList.remove('open'));
        if (!wasOpen) {
            options.classList.add('open');
        }
    } else if (e.target.closest('.custom-select-options')) {
        // Clicked an option, close it
        e.target.closest('.custom-select-options').classList.remove('open');
    } else {
        // Clicked outside, close all
        document.querySelectorAll('.custom-select-options.open').forEach(el => el.classList.remove('open'));
    }
});
