import * as THREE from 'three';

/**
 * Construtor de Tubo Cilíndrico conectado rigidamente entre dois pontos 3D
 */
function createTubeBetween(p1, p2, radius, material) {
    const distance = p1.distanceTo(p2);
    const cylinderGeo = new THREE.CylinderGeometry(radius, radius, distance, 16);
    const cylinder = new THREE.Mesh(cylinderGeo, material);

    const midpoint = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
    cylinder.position.copy(midpoint);

    const direction = new THREE.Vector3().subVectors(p2, p1).normalize();
    const up = new THREE.Vector3(0, 1, 0);
    const quaternion = new THREE.Quaternion().setFromUnitVectors(up, direction);
    cylinder.quaternion.copy(quaternion);

    cylinder.castShadow = true;
    cylinder.receiveShadow = true;
    return cylinder;
}

/**
 * Construtor Procedural do Modelo 3D do Rover Frugal 4WD/4WS
 * - Dimensionamento das Rodas conforme Cálculo de Blondel (2E + P = 64cm -> Roda de Φ 300mm / r_max = 150mm)
 * - Roda com 3 raios curvos e Suspensão Torsional Espiral (C-STS) de Jeong & Kim (2025)
 * - Indicadores visuais de ponto de contato e colisão no solo
 */
export class Rover3DModel {
    constructor() {
        this.group = new THREE.Group();
        this.boxGroup = new THREE.Group();
        this.armsGroup = new THREE.Group();
        this.arms = [];
        this.wheels = [];
        this.cstsModules = [];
        this.steeringKnuckles = [];
        this.rubberBands = [];
        this.contactHalos = [];
        this.boxLid = null;
        this.isLidOpen = false;
        this.isExploded = false;

        // Materiais Realistas
        this.materials = {
            pvc: new THREE.MeshStandardMaterial({
                color: 0xf8fafc,
                roughness: 0.3,
                metalness: 0.05
            }),
            petgOrange: new THREE.MeshStandardMaterial({
                color: 0xff6b22,
                roughness: 0.45,
                metalness: 0.1
            }),
            cstsCyan: new THREE.MeshStandardMaterial({
                color: 0x00e5ff,
                roughness: 0.35,
                metalness: 0.2
            }),
            boxTranslucent: new THREE.MeshPhysicalMaterial({
                color: 0xe0f2fe,
                transparent: true,
                opacity: 0.70,
                roughness: 0.2,
                transmission: 0.8,
                ior: 1.4,
                thickness: 0.8
            }),
            boxLatch: new THREE.MeshStandardMaterial({
                color: 0x1e3a8a,
                roughness: 0.3
            }),
            laptopBody: new THREE.MeshStandardMaterial({
                color: 0x1e293b,
                metalness: 0.7,
                roughness: 0.3
            }),
            laptopScreen: new THREE.MeshBasicMaterial({
                color: 0x00e5ff
            }),
            rubberBand: new THREE.MeshStandardMaterial({
                color: 0xd4a359,
                roughness: 0.9,
                metalness: 0.0
            }),
            rubberTread: new THREE.MeshStandardMaterial({
                color: 0x111827,
                roughness: 0.95
            }),
            metalBolt: new THREE.MeshStandardMaterial({
                color: 0xd1d5db,
                metalness: 0.9,
                roughness: 0.2
            }),
            estopRed: new THREE.MeshStandardMaterial({
                color: 0xd50000,
                roughness: 0.2
            }),
            cameraLens: new THREE.MeshStandardMaterial({
                color: 0x0a0a0a,
                roughness: 0.1,
                metalness: 0.9
            }),
            contactGlow: new THREE.MeshBasicMaterial({
                color: 0x00e5ff,
                transparent: true,
                opacity: 0.6,
                side: THREE.DoubleSide
            })
        };

        this.buildModel();
    }

    buildModel() {
        this.buildOrganizerBox();
        this.buildRigidRadialArms();

        this.group.add(this.boxGroup);
        this.group.add(this.armsGroup);
    }

    buildOrganizerBox() {
        const boxWidth = 0.46;  // 46 cm
        const boxLength = 0.58; // 58 cm
        const boxHeight = 0.24; // 24 cm

        // Corpo da Caixa (Centralizada e Rebaixada em Pêndulo)
        const boxGeo = new THREE.BoxGeometry(boxWidth, boxHeight, boxLength);
        const boxMesh = new THREE.Mesh(boxGeo, this.materials.boxTranslucent);
        boxMesh.castShadow = true;
        boxMesh.receiveShadow = true;
        boxMesh.position.y = 0.05; // Vão livre = 8 cm acima do solo Y = -0.15
        this.boxGroup.add(boxMesh);

        // Borda Superior Reforçada
        const rimGeo = new THREE.BoxGeometry(boxWidth + 0.025, 0.02, boxLength + 0.025);
        const rimMesh = new THREE.Mesh(rimGeo, this.materials.petgOrange);
        rimMesh.position.y = 0.16;
        this.boxGroup.add(rimMesh);

        // Tampa da Caixa
        this.boxLid = new THREE.Group();
        this.boxLid.position.set(0, 0.17, 0);

        const lidGeo = new THREE.BoxGeometry(boxWidth + 0.035, 0.025, boxLength + 0.035);
        const lidMesh = new THREE.Mesh(lidGeo, this.materials.boxTranslucent);
        lidMesh.position.set(0, 0.0125, 0);
        this.boxLid.add(lidMesh);

        // Travas Azuis Laterais
        [-1, 1].forEach(side => {
            const latchGeo = new THREE.BoxGeometry(0.015, 0.05, 0.08);
            const latch = new THREE.Mesh(latchGeo, this.materials.boxLatch);
            latch.position.set(side * (boxWidth / 2 + 0.015), 0.01, 0);
            this.boxLid.add(latch);
        });

        // Câmera FPV
        const camBase = new THREE.Mesh(new THREE.BoxGeometry(0.035, 0.035, 0.035), this.materials.petgOrange);
        camBase.position.set(0, 0.04, -0.22);
        const lens = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.02, 16), this.materials.cameraLens);
        lens.rotation.x = Math.PI / 2;
        lens.position.set(0, 0.04, -0.24);
        this.boxLid.add(camBase); this.boxLid.add(lens);

        // Botão E-Stop (Cogumelo Vermelho)
        const estopBase = new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.022, 0.015, 16), this.materials.petgOrange);
        estopBase.position.set(0.09, 0.035, -0.12);
        const estopBtn = new THREE.Mesh(new THREE.CylinderGeometry(0.026, 0.026, 0.018, 16), this.materials.estopRed);
        estopBtn.position.set(0.09, 0.05, -0.12);
        this.boxLid.add(estopBase); this.boxLid.add(estopBtn);

        this.boxGroup.add(this.boxLid);

        // Notebook Transportado no Interior
        this.buildLaptopInside();
    }

    buildLaptopInside() {
        const laptopGroup = new THREE.Group();
        laptopGroup.position.set(0, -0.04, 0);

        const baseMesh = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.012, 0.30), this.materials.laptopBody);
        laptopGroup.add(baseMesh);

        const kb = new THREE.Mesh(new THREE.PlaneGeometry(0.18, 0.24), new THREE.MeshStandardMaterial({ color: 0x0f172a }));
        kb.rotation.x = -Math.PI / 2;
        kb.position.set(0, 0.007, 0.02);
        laptopGroup.add(kb);

        const screenBase = new THREE.Group();
        screenBase.position.set(0, 0.006, -0.14);

        const scrLid = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.18, 0.008), this.materials.laptopBody);
        scrLid.position.set(0, 0.09, 0);

        const scrDisp = new THREE.Mesh(new THREE.PlaneGeometry(0.20, 0.15), this.materials.laptopScreen);
        scrDisp.position.set(0, 0.09, 0.005);

        screenBase.add(scrLid);
        screenBase.add(scrDisp);
        screenBase.rotation.x = 0.40;

        laptopGroup.add(screenBase);
        this.boxGroup.add(laptopGroup);
    }

    buildRigidRadialArms() {
        const armConfigs = [
            { id: 'FL', xSign: -1, zSign: -1, label: 'Dianteiro Esquerdo' },
            { id: 'FR', xSign: 1,  zSign: -1, label: 'Dianteiro Direito' },
            { id: 'RL', xSign: -1, zSign: 1,  label: 'Traseiro Esquerdo' },
            { id: 'RR', xSign: 1,  zSign: 1,  label: 'Traseiro Direito' }
        ];

        const pipeRadius = 0.014;

        armConfigs.forEach(cfg => {
            const armRoot = new THREE.Group();
            armRoot.name = `Arm_${cfg.id}`;

            // PONTOS GEOMÉTRICOS EXATOS (Dimensionados para Roda de Blondel r_max = 150mm)
            const pClamp = new THREE.Vector3(cfg.xSign * 0.22, 0.14, cfg.zSign * 0.27);
            const pApex = new THREE.Vector3(cfg.xSign * 0.46, 0.42, cfg.zSign * 0.50);
            const pKnuckleTop = new THREE.Vector3(cfg.xSign * 0.66, 0.10, cfg.zSign * 0.68);
            const pWheelCenter = new THREE.Vector3(cfg.xSign * 0.72, 0.00, cfg.zSign * 0.68);

            // A. Abraçadeira Split-Clamp na borda da caixa
            const clamp = new THREE.Mesh(new THREE.BoxGeometry(0.065, 0.065, 0.065), this.materials.petgOrange);
            clamp.position.copy(pClamp);
            armRoot.add(clamp);

            // B. Haste Superior de PVC (Ascendente)
            const pipeAsc = createTubeBetween(pClamp, pApex, pipeRadius, this.materials.pvc);
            armRoot.add(pipeAsc);

            // C. Vértice Superior 3D (Junta no ápice do V)
            const apexMesh = new THREE.Mesh(new THREE.SphereGeometry(0.038, 16, 16), this.materials.petgOrange);
            apexMesh.position.copy(pApex);
            armRoot.add(apexMesh);

            // D. Haste Inferior de PVC (Descendente)
            const pipeDesc = createTubeBetween(pApex, pKnuckleTop, pipeRadius, this.materials.pvc);
            armRoot.add(pipeDesc);

            // E. Suporte Inferior do Braço
            const lowerBracket = new THREE.Mesh(new THREE.BoxGeometry(0.055, 0.055, 0.055), this.materials.petgOrange);
            lowerBracket.position.copy(pKnuckleTop);
            armRoot.add(lowerBracket);

            // F. Módulo Móvel de Esterçamento 4WS
            const knuckleGroup = new THREE.Group();
            knuckleGroup.position.copy(pWheelCenter);

            const knuckleBody = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.09, 0.06), this.materials.petgOrange);
            knuckleBody.position.set(0, 0.03, 0);
            knuckleGroup.add(knuckleBody);

            const servo = new THREE.Mesh(new THREE.BoxGeometry(0.045, 0.04, 0.05), this.materials.laptopBody);
            servo.position.set(0, 0.085, 0);
            knuckleGroup.add(servo);

            // Elásticos de Suspensão Complacente Linear
            const rubberGroup = new THREE.Group();
            for (let b = -1; b <= 1; b += 2) {
                const bandGeo = new THREE.CylinderGeometry(0.0035, 0.0035, 0.09, 8);
                const bandMesh = new THREE.Mesh(bandGeo, this.materials.rubberBand);
                bandMesh.position.set(b * 0.022, 0.03, 0);
                rubberGroup.add(bandMesh);
            }
            knuckleGroup.add(rubberGroup);
            this.rubberBands.push(rubberGroup);

            // Motorredutor de Tração 4WD
            const motorMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.06, 16), this.materials.laptopBody);
            motorMesh.rotation.z = Math.PI / 2;
            motorMesh.position.set(cfg.xSign * 0.02, 0, 0);
            knuckleGroup.add(motorMesh);

            // Roda de 3 Raios Curvos com Módulo C-STS Dimensionada por Blondel (r_max = 150mm)
            const { wheelGroup, cstsGroup } = this.buildBlondelCurvedSpokeWheel(cfg.xSign);
            wheelGroup.position.set(cfg.xSign * 0.065, 0, 0);
            knuckleGroup.add(wheelGroup);

            // Halo Indicador de Ponto de Contato no Solo / Degrau
            const haloGeo = new THREE.RingGeometry(0.03, 0.07, 16);
            const haloMesh = new THREE.Mesh(haloGeo, this.materials.contactGlow);
            haloMesh.rotation.x = -Math.PI / 2;
            haloMesh.position.set(0, -0.145, 0);
            knuckleGroup.add(haloMesh);
            this.contactHalos.push(haloMesh);

            this.steeringKnuckles.push(knuckleGroup);
            this.wheels.push(wheelGroup);
            this.cstsModules.push(cstsGroup);

            armRoot.add(knuckleGroup);
            this.arms.push(armRoot);
            this.armsGroup.add(armRoot);
        });
    }

    /**
     * Roda de 3 Raios Curvos Dimensionada para Degraus de Blondel (2E + P = 64cm)
     * - r_max = 150 mm (Diâmetro total = 300 mm)
     * - r_min = 45 mm (Diâmetro do cubo C-STS = 90 mm)
     */
    buildBlondelCurvedSpokeWheel(xDirection) {
        const wheelGroup = new THREE.Group();
        const wheelRadius = 0.15; // 300 mm de diâmetro (r_max de Blondel)
        const hubRadius = 0.045;  // 90 mm de diâmetro do cubo C-STS
        const numSpokes = 3;

        // 1. MÓDULO C-STS NO CUBO
        const cstsGroup = new THREE.Group();
        const innerRing = new THREE.Mesh(
            new THREE.CylinderGeometry(0.018, 0.018, 0.025, 16),
            this.materials.petgOrange
        );
        innerRing.rotation.z = Math.PI / 2;
        cstsGroup.add(innerRing);

        // Mola Espiral Plana C-STS
        const spiralShape = new THREE.Shape();
        const spiralPoints = [];
        const spiralTurns = 1.8;
        const spiralSteps = 30;
        for (let i = 0; i <= spiralSteps; i++) {
            const t = i / spiralSteps;
            const r = 0.020 + t * (hubRadius - 0.020);
            const theta = t * Math.PI * 2 * spiralTurns * xDirection;
            spiralPoints.push(new THREE.Vector2(Math.cos(theta) * r, Math.sin(theta) * r));
        }
        spiralShape.moveTo(spiralPoints[0].x, spiralPoints[0].y);
        for (let i = 1; i <= spiralSteps; i++) spiralShape.lineTo(spiralPoints[i].x, spiralPoints[i].y);
        for (let i = spiralSteps; i >= 0; i--) {
            const t = i / spiralSteps;
            const r = 0.016 + t * (hubRadius - 0.020);
            const theta = t * Math.PI * 2 * spiralTurns * xDirection;
            spiralShape.lineTo(Math.cos(theta) * r, Math.sin(theta) * r);
        }
        spiralShape.closePath();

        const spiralGeo = new THREE.ExtrudeGeometry(spiralShape, { depth: 0.018, bevelEnabled: false });
        const spiralMesh = new THREE.Mesh(spiralGeo, this.materials.cstsCyan);
        spiralMesh.rotation.y = Math.PI / 2;
        spiralMesh.position.x = -0.009;
        cstsGroup.add(spiralMesh);

        const outerRing = new THREE.Mesh(
            new THREE.TorusGeometry(hubRadius, 0.006, 8, 24),
            this.materials.petgOrange
        );
        outerRing.rotation.y = Math.PI / 2;
        cstsGroup.add(outerRing);

        wheelGroup.add(cstsGroup);

        // 2. 3 RAIOS CURVOS ESPIRALADOS (Cálculo de Blondel)
        for (let s = 0; s < numSpokes; s++) {
            const spokeShape = new THREE.Shape();
            const angleOffset = (s * Math.PI * 2) / numSpokes;

            const points = [];
            const steps = 18;
            for (let i = 0; i <= steps; i++) {
                const t = i / steps;
                const r = hubRadius + t * (wheelRadius - hubRadius);
                const theta = angleOffset + Math.pow(t, 0.85) * 1.55 * xDirection;
                points.push(new THREE.Vector2(Math.cos(theta) * r, Math.sin(theta) * r));
            }

            spokeShape.moveTo(points[0].x, points[0].y);
            for (let i = 1; i <= steps; i++) spokeShape.lineTo(points[i].x, points[i].y);
            for (let i = steps; i >= 0; i--) {
                const t = i / steps;
                const r = (hubRadius - 0.008) + t * (wheelRadius - hubRadius);
                const theta = angleOffset + Math.pow(t, 0.85) * 1.55 * xDirection + 0.15 * (1 - t * 0.3);
                spokeShape.lineTo(Math.cos(theta) * r, Math.sin(theta) * r);
            }
            spokeShape.closePath();

            const spokeGeo = new THREE.ExtrudeGeometry(spokeShape, {
                depth: 0.022,
                bevelEnabled: true,
                bevelSegments: 2,
                bevelSize: 0.002,
                bevelThickness: 0.002
            });
            const spokeMesh = new THREE.Mesh(spokeGeo, this.materials.petgOrange);
            spokeMesh.rotation.y = Math.PI / 2;
            spokeMesh.position.x = -0.011;
            wheelGroup.add(spokeMesh);

            // Garra de Borracha na Extremidade do Raio
            const tipPoint = points[steps];
            const gripGeo = new THREE.BoxGeometry(0.028, 0.014, 0.030);
            const gripMesh = new THREE.Mesh(gripGeo, this.materials.rubberTread);
            gripMesh.position.set(0, tipPoint.y, tipPoint.x);
            wheelGroup.add(gripMesh);
        }

        const bolt = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.04, 8), this.materials.metalBolt);
        bolt.rotation.z = Math.PI / 2;
        wheelGroup.add(bolt);

        return { wheelGroup, cstsGroup };
    }

    setSteeringAngles(angles) {
        for (let i = 0; i < 4; i++) {
            if (this.steeringKnuckles[i]) {
                this.steeringKnuckles[i].rotation.y = angles[i];
            }
        }
    }

    rotateWheels(deltaRotation) {
        this.wheels.forEach(w => {
            w.rotation.x += deltaRotation;
        });
    }

    setWheelContactState(wheelIdx, isContact, normalForce) {
        if (this.contactHalos[wheelIdx]) {
            this.contactHalos[wheelIdx].visible = isContact;
            const opacity = Math.min(0.9, 0.3 + (normalForce / 50));
            this.contactHalos[wheelIdx].material.opacity = opacity;
        }
    }

    updateSuspensionCompliance(bounceAmount) {
        this.rubberBands.forEach((rb, idx) => {
            const scaleY = 1.0 + Math.sin(Date.now() * 0.015 + idx) * bounceAmount;
            rb.scale.set(1.0, scaleY, 1.0);
        });

        this.cstsModules.forEach((csts, idx) => {
            const torsionalDeflection = Math.sin(Date.now() * 0.02 + idx) * (bounceAmount * 0.8);
            csts.rotation.x = torsionalDeflection;
        });
    }

    toggleBoxLid() {
        this.isLidOpen = !this.isLidOpen;
        this.boxLid.rotation.x = this.isLidOpen ? -1.6 : 0;
    }

    toggleExplodedView() {
        this.isExploded = !this.isExploded;
        const offset = this.isExploded ? 0.15 : 0;

        this.arms.forEach((arm, i) => {
            const xSign = (i % 2 === 0) ? -1 : 1;
            const zSign = (i < 2) ? -1 : 1;
            arm.position.x = xSign * offset;
            arm.position.z = zSign * offset;
            arm.position.y = offset * 0.4;
        });

        this.boxGroup.position.y = this.isExploded ? -0.12 : 0;
    }
}
