// =============================================================================
//  TERRENO — Percurso de homologação no Itaipu Parquetec
//
//  O cenário deixa de ser "três degraus soltos" e passa a ser o percurso real
//  descrito em 05_Execucao_Testes_e_Operacao/03: base -> calçada -> rampa de
//  acessibilidade -> meio-fio -> ponto de coleta -> escada -> porta estreita ->
//  sala da T.I.
//
//  O terreno é uma lista de caixas alinhadas aos eixos. `alturaEm(x, z)` devolve
//  a cota do topo mais alto que contém o ponto — é a mesma consulta que o
//  simulador Python faz com `PerfilEscada.altura`.
// =============================================================================

import * as THREE from 'three';
import { PARAMETROS } from './parametros.js';

const ESC = PARAMETROS.ambiente.escada;

export class Terreno {
    constructor() {
        this.caixas = [];      // { x0, x1, z0, z1, y, tipo }
        this.paredes = [];     // { x0, x1, z0, z1, altura }
        this.grupo = new THREE.Group();
        this.narizes = [];     // arestas de degrau, para o HUD
        this.construir();
    }

    // -- API de consulta -------------------------------------------------
    alturaEm(x, z) {
        let y = 0.0;
        for (const c of this.caixas) {
            if (x >= c.x0 && x <= c.x1 && z >= c.z0 && z <= c.z1 && c.y > y) y = c.y;
        }
        return y;
    }

    /** Perfil de alturas ao longo da direção de avanço, para a física da roda. */
    perfilLongitudinal(x, z, direcao, amostras, alcance) {
        const saida = new Float32Array(amostras);
        for (let i = 0; i < amostras; i++) {
            const s = (i / (amostras - 1) - 0.5) * alcance;
            saida[i] = this.alturaEm(x + direcao.x * s, z + direcao.z * s);
        }
        return saida;
    }

    colideComParede(x, z, raio) {
        for (const p of this.paredes) {
            if (x > p.x0 - raio && x < p.x1 + raio && z > p.z0 - raio && z < p.z1 + raio) return true;
        }
        return false;
    }

    // -- Construção ------------------------------------------------------
    _caixa(x0, x1, z0, z1, y, tipo, material) {
        this.caixas.push({ x0, x1, z0, z1, y, tipo });
        if (y > 0.0001) {
            const geo = new THREE.BoxGeometry(x1 - x0, y, z1 - z0);
            const malha = new THREE.Mesh(geo, material);
            malha.position.set((x0 + x1) / 2, y / 2, (z0 + z1) / 2);
            malha.castShadow = true; malha.receiveShadow = true;
            this.grupo.add(malha);
        }
    }

    _parede(x0, x1, z0, z1, altura, material) {
        this.paredes.push({ x0, x1, z0, z1, altura });
        const geo = new THREE.BoxGeometry(x1 - x0, altura, z1 - z0);
        const malha = new THREE.Mesh(geo, material);
        malha.position.set((x0 + x1) / 2, altura / 2, (z0 + z1) / 2);
        malha.castShadow = true; malha.receiveShadow = true;
        this.grupo.add(malha);
    }

    construir() {
        const mConcreto = new THREE.MeshStandardMaterial({ color: 0x5a6472, roughness: 0.85 });
        const mDegrau = new THREE.MeshStandardMaterial({ color: 0x6b7684, roughness: 0.8 });
        const mParede = new THREE.MeshStandardMaterial({ color: 0x2f3846, roughness: 0.9 });
        const mRampa = new THREE.MeshStandardMaterial({ color: 0x4d7c5f, roughness: 0.85 });

        // --- 1. Meio-fio entre a via e a calçada (z de -6 a -8) -----------
        this._caixa(-4, 4, -9.5, -6.0, PARAMETROS.ambiente.meio_fio.altura_tipica,
                    'meio-fio', mConcreto);

        // --- 2. Rampa de acessibilidade (aproximada por lances curtos) ----
        const alturaRampa = 0.30, passosRampa = 10;
        for (let i = 0; i < passosRampa; i++) {
            const z0 = -13.0 + i * 0.35;
            this._caixa(-2.2, 2.2, z0, z0 + 0.35,
                        PARAMETROS.ambiente.meio_fio.altura_tipica + alturaRampa * (i + 1) / passosRampa,
                        'rampa', mRampa);
        }
        this._caixa(-2.2, 2.2, -16.0, -9.5,
                    PARAMETROS.ambiente.meio_fio.altura_tipica + alturaRampa, 'patamar', mConcreto);

        // --- 3. Escadaria de Blondel (lance completo) --------------------
        const zEscada = -17.0;
        const baseEscada = PARAMETROS.ambiente.meio_fio.altura_tipica + alturaRampa;
        for (let i = 0; i < ESC.num_degraus_lance; i++) {
            const z0 = zEscada - (i + 1) * ESC.piso_P;
            const y = baseEscada + (i + 1) * ESC.espelho_E;
            this._caixa(-ESC.largura / 2, ESC.largura / 2, z0, zEscada - i * ESC.piso_P, y,
                        'degrau', mDegrau);
            this.narizes.push({ z: zEscada - i * ESC.piso_P, y });
        }
        const zTopo = zEscada - ESC.num_degraus_lance * ESC.piso_P;
        const yTopo = baseEscada + ESC.num_degraus_lance * ESC.espelho_E;
        this._caixa(-3.0, 3.0, zTopo - 7.0, zTopo, yTopo, 'patamar-superior', mConcreto);

        // --- 4. Porta estreita e corredor da T.I. -------------------------
        const vao = PARAMETROS.ambiente.porta_estreita;
        const zPorta = zTopo - 2.2;
        this._parede(-3.0, -vao / 2, zPorta, zPorta + 0.2, 2.2 + yTopo, mParede);
        this._parede(vao / 2, 3.0, zPorta, zPorta + 0.2, 2.2 + yTopo, mParede);
        const corredor = PARAMETROS.ambiente.corredor_estreito;
        this._parede(-corredor / 2 - 0.15, -corredor / 2, zPorta - 4.5, zPorta, 2.2 + yTopo, mParede);
        this._parede(corredor / 2, corredor / 2 + 0.15, zPorta - 4.5, zPorta, 2.2 + yTopo, mParede);

        // --- 5. Marcações de missão ---------------------------------------
        this.pontoColeta = new THREE.Vector3(0, baseEscada, -14.0);
        this.pontoEntrega = new THREE.Vector3(0, yTopo, zPorta - 3.6);
        this.pontoBase = new THREE.Vector3(0, 0, -1.0);

        this.grupo.add(this._marcador(this.pontoColeta, 0x00b0ff));
        this.grupo.add(this._marcador(this.pontoEntrega, 0x00c853));
        this.grupo.add(this._marcador(this.pontoBase, 0xffa000));

        // --- 6. Piso base -------------------------------------------------
        const piso = new THREE.Mesh(
            new THREE.PlaneGeometry(120, 120),
            new THREE.MeshStandardMaterial({ color: 0x1b2230, roughness: 0.95 }),
        );
        piso.rotation.x = -Math.PI / 2;
        piso.receiveShadow = true;
        this.grupo.add(piso);

        const grade = new THREE.GridHelper(120, 120, 0x2b6f86, 0x1e2836);
        grade.position.y = 0.002;
        this.grupo.add(grade);
    }

    _marcador(posicao, cor) {
        const g = new THREE.Group();
        const anel = new THREE.Mesh(
            new THREE.RingGeometry(0.30, 0.40, 32),
            new THREE.MeshBasicMaterial({ color: cor, transparent: true, opacity: 0.55,
                                          side: THREE.DoubleSide }),
        );
        anel.rotation.x = -Math.PI / 2;
        anel.position.copy(posicao);
        anel.position.y += 0.01;
        g.add(anel);
        const feixe = new THREE.Mesh(
            new THREE.CylinderGeometry(0.022, 0.022, 0.9, 10),
            new THREE.MeshBasicMaterial({ color: cor, transparent: true, opacity: 0.16 }),
        );
        feixe.position.copy(posicao);
        feixe.position.y += 0.45;
        g.add(feixe);
        return g;
    }
}
