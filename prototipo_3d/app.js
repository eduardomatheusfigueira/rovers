import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { Rover3DModel } from './rover_model.js';

// ==========================================
// CONFIGURAÇÃO DO CENÁRIO E THREE.JS
// ==========================================
const container = document.getElementById('canvas-container');

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b0f19);
scene.fog = new THREE.FogExp2(0x0b0f19, 0.035);

const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(2.4, 1.8, 2.8);

const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.2;
container.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.maxPolarAngle = Math.PI / 2 - 0.02;
controls.minDistance = 0.8;
controls.maxDistance = 15;
controls.target.set(0, 0.2, 0);

// Luzes
scene.add(new THREE.AmbientLight(0xffffff, 0.85));
const dirLight = new THREE.DirectionalLight(0xfff7ed, 1.8);
dirLight.position.set(5, 8, 5);
dirLight.castShadow = true;
dirLight.shadow.mapSize.width = 2048;
dirLight.shadow.mapSize.height = 2048;
scene.add(dirLight);

const cyanLight = new THREE.DirectionalLight(0x00e5ff, 0.6);
cyanLight.position.set(-5, 3, -5);
scene.add(cyanLight);

// Chão Base (Y = -0.15)
const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(50, 50),
    new THREE.MeshStandardMaterial({ color: 0x131926, roughness: 0.4, metalness: 0.2 })
);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -0.15;
floor.receiveShadow = true;
scene.add(floor);

const grid = new THREE.GridHelper(50, 50, 0x00e5ff, 0x1e293b);
grid.position.y = -0.149;
scene.add(grid);

// ==========================================
// ESCADA CONFORME A LEI DE BLONDEL
// Espelho E = 17 cm (0.17m) | Piso P = 30 cm (0.30m) -> 2E + P = 64 cm
// ==========================================
const stairGroup = new THREE.Group();
const stepHeight = 0.17;
const stepDepth = 0.30;
const stairStart = -2.0;

for (let i = 0; i < 3; i++) {
    const step = new THREE.Mesh(
        new THREE.BoxGeometry(2.0, stepHeight * (i + 1), stepDepth),
        new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.65, metalness: 0.1 })
    );
    step.position.set(0, -0.15 + (stepHeight * (i + 1)) / 2, stairStart - (i * stepDepth) - (stepDepth / 2));
    step.castShadow = true; step.receiveShadow = true;
    stairGroup.add(step);
}

const plat = new THREE.Mesh(
    new THREE.BoxGeometry(2.0, stepHeight * 3, 2.0),
    new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.65, metalness: 0.1 })
);
plat.position.set(0, -0.15 + (stepHeight * 3) / 2, stairStart - (3 * stepDepth) - 1.0);
plat.castShadow = true; plat.receiveShadow = true;
stairGroup.add(plat);
scene.add(stairGroup);

function getTerrainHeight(x, z) {
    if (Math.abs(x) < 1.0) {
        if (z <= stairStart - 3 * stepDepth) {
            return -0.15 + stepHeight * 3;
        } else if (z <= stairStart - 2 * stepDepth) {
            return -0.15 + stepHeight * 3;
        } else if (z <= stairStart - 1 * stepDepth) {
            return -0.15 + stepHeight * 2;
        } else if (z <= stairStart) {
            return -0.15 + stepHeight * 1;
        }
    }
    return -0.15;
}

// Instanciar Modelo 3D
const rover = new Rover3DModel();
scene.add(rover.group);

// ==========================================
// ESTADO DO VEÍCULO E MOTOR DE FÍSICA
// ==========================================
const roverState = {
    x: 0, z: 0, y: 0, heading: 0, pitch: 0, roll: 0,
    speed: 0, maxSpeed: 1.5, accel: 2.5, decel: 3.5,
    steerAngle: 0, maxSteerAngle: Math.PI / 4,
    steerMode: 'ackermann', cameraMode: 'orbit', isEStopped: false, keys: {},
    wheelHeights: [0, 0, 0, 0],
    normalForces: [18.5, 18.5, 18.5, 18.5]
};

window.addEventListener('keydown', e => { roverState.keys[e.key.toLowerCase()] = true; });
window.addEventListener('keyup', e => { roverState.keys[e.key.toLowerCase()] = false; });

document.querySelectorAll('.btn-mode').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.btn-mode').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        roverState.steerMode = btn.dataset.mode;
    });
});

document.querySelectorAll('.btn-cam').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.btn-cam').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const mode = btn.id.replace('cam-', '');
        roverState.cameraMode = mode;
        controls.enabled = (mode === 'orbit');
    });
});

document.getElementById('btn-toggle-box')?.addEventListener('click', () => { rover.toggleBoxLid(); });
document.getElementById('btn-toggle-explode')?.addEventListener('click', () => { rover.toggleExplodedView(); });

document.getElementById('btn-estop')?.addEventListener('click', () => {
    roverState.isEStopped = !roverState.isEStopped;
    const btn = document.getElementById('btn-estop');
    btn.textContent = roverState.isEStopped ? '⚡ Reativar Sistema' : '🛑 Parada Emergência (E-Stop)';
    btn.style.background = roverState.isEStopped ? 'red' : '';
    if (roverState.isEStopped) roverState.speed = 0;
});

document.getElementById('btn-test-stairs')?.addEventListener('click', () => {
    roverState.x = 0; roverState.z = -1.0; roverState.heading = 0;
    roverState.steerMode = 'stair';
    document.querySelectorAll('.btn-mode').forEach(b => b.classList.remove('active'));
    document.getElementById('btn-mode-stair')?.classList.add('active');
});

const setupDpad = (id, key) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('mousedown', () => { roverState.keys[key] = true; });
    el.addEventListener('mouseup', () => { roverState.keys[key] = false; });
    el.addEventListener('touchstart', e => { e.preventDefault(); roverState.keys[key] = true; });
    el.addEventListener('touchend', e => { e.preventDefault(); roverState.keys[key] = false; });
};
setupDpad('dpad-up', 'w'); setupDpad('dpad-down', 's');
setupDpad('dpad-left', 'a'); setupDpad('dpad-right', 'd');
document.getElementById('dpad-stop')?.addEventListener('click', () => { roverState.speed = 0; });

let lastTime = performance.now();
function animate(currentTime) {
    requestAnimationFrame(animate);
    const dt = Math.min((currentTime - lastTime) / 1000, 0.1);
    lastTime = currentTime;

    if (!roverState.isEStopped) {
        const throttle = (roverState.keys['w'] || roverState.keys['arrowup']) ? 1 :
                         (roverState.keys['s'] || roverState.keys['arrowdown']) ? -1 : 0;
        if (throttle !== 0) {
            roverState.speed = THREE.MathUtils.clamp(roverState.speed + throttle * roverState.accel * dt, -0.7, roverState.maxSpeed);
        } else {
            roverState.speed = THREE.MathUtils.damp(roverState.speed, 0, 3.5, dt);
        }
        if (roverState.keys[' ']) roverState.speed = THREE.MathUtils.damp(roverState.speed, 0, 8, dt);

        const steerDir = (roverState.keys['a'] || roverState.keys['arrowleft']) ? 1 :
                        (roverState.keys['d'] || roverState.keys['arrowright']) ? -1 : 0;
        roverState.steerAngle = THREE.MathUtils.damp(roverState.steerAngle, steerDir * roverState.maxSteerAngle, 6, dt);

        let steerAngles = [0, 0, 0, 0], vx = 0, vz = 0, yawRate = 0;
        switch (roverState.steerMode) {
            case 'ackermann':
                steerAngles = [roverState.steerAngle, roverState.steerAngle, -roverState.steerAngle, -roverState.steerAngle];
                yawRate = (roverState.speed / 0.8) * Math.sin(roverState.steerAngle) * 1.5;
                roverState.heading += yawRate * dt;
                vx = -Math.sin(roverState.heading) * roverState.speed;
                vz = -Math.cos(roverState.heading) * roverState.speed;
                break;
            case 'crab':
                steerAngles = [roverState.steerAngle, roverState.steerAngle, roverState.steerAngle, roverState.steerAngle];
                const crabH = roverState.heading + roverState.steerAngle;
                vx = -Math.sin(crabH) * roverState.speed;
                vz = -Math.cos(crabH) * roverState.speed;
                break;
            case 'spin':
                const spinAngle = Math.PI / 4;
                steerAngles = [spinAngle, -spinAngle, -spinAngle, spinAngle];
                if (Math.abs(roverState.speed) > 0.05) roverState.heading += (roverState.speed / 0.4) * dt;
                break;
            case 'stair':
                steerAngles = [0, 0, 0, 0];
                vx = -Math.sin(roverState.heading) * roverState.speed * 0.75;
                vz = -Math.cos(roverState.heading) * roverState.speed * 0.75;
                break;
        }

        roverState.x += vx * dt;
        roverState.z += vz * dt;

        // Colisão Independente das 4 Rodas
        const wheelOffsets = [
            { x: -0.72, z: -0.68 },
            { x:  0.72, z: -0.68 },
            { x: -0.72, z:  0.68 },
            { x:  0.72, z:  0.68 }
        ];

        const curWheelY = [];
        for (let i = 0; i < 4; i++) {
            const localOff = new THREE.Vector3(wheelOffsets[i].x, 0, wheelOffsets[i].z).applyAxisAngle(new THREE.Vector3(0, 1, 0), roverState.heading);
            const wx = roverState.x + localOff.x;
            const wz = roverState.z + localOff.z;

            const terrainY = getTerrainHeight(wx, wz);
            const targetY = terrainY + 0.15;
            roverState.wheelHeights[i] = THREE.MathUtils.damp(roverState.wheelHeights[i], targetY, 10, dt);
            curWheelY.push(roverState.wheelHeights[i]);

            const isContact = Math.abs(roverState.wheelHeights[i] - targetY) < 0.03;
            rover.setWheelContactState(i, isContact, roverState.normalForces[i]);
        }

        const frontY = (curWheelY[0] + curWheelY[1]) / 2;
        const rearY = (curWheelY[2] + curWheelY[3]) / 2;
        const leftY = (curWheelY[0] + curWheelY[2]) / 2;
        const rightY = (curWheelY[1] + curWheelY[3]) / 2;

        const targetBodyY = (frontY + rearY) / 2;
        const targetPitch = Math.atan2(frontY - rearY, 1.36);
        const targetRoll = Math.atan2(rightY - leftY, 1.44);

        roverState.y = THREE.MathUtils.damp(roverState.y, targetBodyY, 8, dt);
        roverState.pitch = THREE.MathUtils.damp(roverState.pitch, targetPitch, 8, dt);
        roverState.roll = THREE.MathUtils.damp(roverState.roll, targetRoll, 8, dt);

        const totalWeight = 74.0;
        const pitchFactor = Math.sin(roverState.pitch);
        roverState.normalForces[0] = Math.max(2, (totalWeight / 4) - pitchFactor * 12);
        roverState.normalForces[1] = Math.max(2, (totalWeight / 4) - pitchFactor * 12);
        roverState.normalForces[2] = Math.max(2, (totalWeight / 4) + pitchFactor * 12);
        roverState.normalForces[3] = Math.max(2, (totalWeight / 4) + pitchFactor * 12);

        rover.boxGroup.rotation.x = -(roverState.speed / roverState.maxSpeed) * 0.04 + roverState.pitch * 0.7;

        rover.group.position.set(roverState.x, roverState.y, roverState.z);
        rover.group.rotation.y = roverState.heading;
        rover.group.rotation.x = roverState.pitch;
        rover.group.rotation.z = roverState.roll;

        rover.setSteeringAngles(steerAngles);
        rover.rotateWheels(roverState.speed * dt * 7);

        const bounce = (Math.abs(roverState.speed) > 0.1) ? 0.08 : 0.01;
        rover.updateSuspensionCompliance(bounce);

        // Câmeras
        if (roverState.cameraMode === 'orbit') {
            controls.target.set(roverState.x, roverState.y + 0.15, roverState.z);
        } else if (roverState.cameraMode === 'fpv') {
            const fpvPos = new THREE.Vector3(0, 0.24, -0.24).applyAxisAngle(new THREE.Vector3(0, 1, 0), roverState.heading).add(new THREE.Vector3(roverState.x, roverState.y, roverState.z));
            camera.position.copy(fpvPos);
            const look = new THREE.Vector3(0, 0.20, -2.5).applyAxisAngle(new THREE.Vector3(0, 1, 0), roverState.heading).add(new THREE.Vector3(roverState.x, roverState.y, roverState.z));
            camera.lookAt(look);
        } else if (roverState.cameraMode === 'top') {
            camera.position.set(roverState.x, roverState.y + 4.2, roverState.z + 0.01);
            camera.lookAt(roverState.x, roverState.y, roverState.z);
        } else if (roverState.cameraMode === 'side') {
            const side = new THREE.Vector3(2.4, 0.4, 0).applyAxisAngle(new THREE.Vector3(0, 1, 0), roverState.heading);
            camera.position.copy(new THREE.Vector3(roverState.x, roverState.y, roverState.z).add(side));
            camera.lookAt(roverState.x, roverState.y + 0.15, roverState.z);
        }

        // HUD Telemetria
        const speedMs = Math.abs(roverState.speed);
        const speedEl = document.getElementById('val-speed');
        if (speedEl) speedEl.innerHTML = `${speedMs.toFixed(2)} <small>m/s</small>`;
        const speedBar = document.getElementById('bar-speed');
        if (speedBar) speedBar.style.width = `${(speedMs / roverState.maxSpeed) * 100}%`;
        const rpm = Math.round((speedMs / (0.30 * Math.PI)) * 60);
        const rpmEl = document.getElementById('val-rpm');
        if (rpmEl) rpmEl.innerHTML = `${rpm} <small>RPM</small>`;
        const rpmBar = document.getElementById('bar-rpm');
        if (rpmBar) rpmBar.style.width = `${(rpm / 120) * 100}%`;
        const pitchEl = document.getElementById('val-pitch');
        if (pitchEl) pitchEl.textContent = `${(roverState.pitch * 57.3).toFixed(1)}°`;
        const rollEl = document.getElementById('val-roll');
        if (rollEl) rollEl.textContent = `${(roverState.roll * 57.3).toFixed(1)}°`;
        const horizon = document.getElementById('horizon-disc');
        if (horizon) horizon.style.transform = `rotate(${-roverState.roll * 57.3}deg) translateY(${roverState.pitch * 35}px)`;

        const fzFL = document.getElementById('fz-fl');
        if (fzFL) fzFL.textContent = `${roverState.normalForces[0].toFixed(1)} N`;
        const fzFR = document.getElementById('fz-fr');
        if (fzFR) fzFR.textContent = `${roverState.normalForces[1].toFixed(1)} N`;
        const fzRL = document.getElementById('fz-rl');
        if (fzRL) fzRL.textContent = `${roverState.normalForces[2].toFixed(1)} N`;
        const fzRR = document.getElementById('fz-rr');
        if (fzRR) fzRR.textContent = `${roverState.normalForces[3].toFixed(1)} N`;
    }

    if (roverState.cameraMode === 'orbit') controls.update();
    renderer.render(scene, camera);
}
requestAnimationFrame(animate);

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});
