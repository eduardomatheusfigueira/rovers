// =============================================================================
//  MODELO 3D PARAMÉTRICO DO ROVER
//
//  Toda a geometria vem de `parametros.js` (gerado do YAML mestre). Mudar o
//  diâmetro da roda ou o entre-eixos no arquivo mestre muda o modelo 3D, o
//  simulador Python e a documentação ao mesmo tempo — não há mais três
//  geometrias diferentes convivendo no repositório.
// =============================================================================

import * as THREE from 'three';
import { PARAMETROS, POSICOES_RODAS, IDS_RODAS } from './parametros.js';
import { perfilRaios, OFFSET_CG } from './fisica.js';

const R = PARAMETROS.roda;
const V = PARAMETROS.veiculo;
const CS = PARAMETROS.csts;

function tuboEntre(p1, p2, raio, material) {
    const dist = p1.distanceTo(p2);
    const malha = new THREE.Mesh(new THREE.CylinderGeometry(raio, raio, dist, 14), material);
    malha.position.copy(new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5));
    malha.quaternion.setFromUnitVectors(
        new THREE.Vector3(0, 1, 0),
        new THREE.Vector3().subVectors(p2, p1).normalize(),
    );
    malha.castShadow = true; malha.receiveShadow = true;
    return malha;
}

export class ModeloRover {
    constructor(opcoes = {}) {
        this.raioMax = opcoes.raioMax || R.raio_max;
        this.raioCubo = opcoes.raioCubo || R.raio_cubo;
        this.grupo = new THREE.Group();
        this.grupoCaixa = new THREE.Group();
        this.bracos = {};
        this.mangas = {};
        this.rodas = {};
        this.modulosCsts = {};
        this.elasticos = {};
        this.halos = {};
        this.tampaAberta = false;
        this.explodido = false;
        this.notebook = null;

        this.materiais = {
            pvc: new THREE.MeshStandardMaterial({ color: 0xf1f5f9, roughness: 0.35, metalness: 0.05 }),
            petg: new THREE.MeshStandardMaterial({ color: 0xff6b22, roughness: 0.45, metalness: 0.1 }),
            csts: new THREE.MeshStandardMaterial({ color: 0x00e5ff, roughness: 0.3, metalness: 0.25 }),
            aro: new THREE.MeshStandardMaterial({ color: 0x2a3240, roughness: 0.95 }),
            caixa: new THREE.MeshPhysicalMaterial({
                color: 0xdff1fb, transparent: true, opacity: 0.42, roughness: 0.15,
                transmission: 0.75, thickness: 0.5, side: THREE.DoubleSide,
            }),
            escuro: new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.65, roughness: 0.35 }),
            metal: new THREE.MeshStandardMaterial({ color: 0xcbd5e1, metalness: 0.9, roughness: 0.2 }),
            elastico: new THREE.MeshStandardMaterial({ color: 0xd4a359, roughness: 0.9 }),
            bateria: new THREE.MeshStandardMaterial({ color: 0x14532d, roughness: 0.6 }),
            tela: new THREE.MeshBasicMaterial({ color: 0x22d3ee }),
            halo: new THREE.MeshBasicMaterial({ color: 0x00e5ff, transparent: true,
                                               opacity: 0.5, side: THREE.DoubleSide }),
        };

        this.construir();
    }

    construir() {
        this.construirCaixa();
        this.construirBracos();
        this.grupo.add(this.grupoCaixa);
    }

    // -- caixa organizadora pendular ------------------------------------
    construirCaixa() {
        const larguraCaixa = 0.42, profundidade = 0.34, altura = V.altura_caixa;
        const yFundo = V.vao_livre_ventre - V.altura_cg_chassi;   // ambas medidas do solo

        const paredes = new THREE.Mesh(
            new THREE.BoxGeometry(larguraCaixa, altura, profundidade),
            this.materiais.caixa,
        );
        paredes.position.y = yFundo + altura / 2;
        paredes.castShadow = true;
        this.grupoCaixa.add(paredes);

        const fundo = new THREE.Mesh(
            new THREE.BoxGeometry(larguraCaixa, 0.012, profundidade),
            this.materiais.escuro,
        );
        fundo.position.y = yFundo;
        this.grupoCaixa.add(fundo);

        this.tampa = new THREE.Group();
        const tampaMalha = new THREE.Mesh(
            new THREE.BoxGeometry(larguraCaixa + 0.02, 0.014, profundidade + 0.02),
            this.materiais.caixa,
        );
        tampaMalha.position.set(0, 0, profundidade / 2);
        this.tampa.add(tampaMalha);
        this.tampa.position.set(0, yFundo + altura, -profundidade / 2);
        this.grupoCaixa.add(this.tampa);

        // Bateria e eletrônica no fundo: é isso que rebaixa o CG
        const bat = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.05, 0.09), this.materiais.bateria);
        bat.position.set(-0.11, yFundo + 0.035, 0);
        this.grupoCaixa.add(bat);
        const pdb = new THREE.Mesh(new THREE.BoxGeometry(0.11, 0.03, 0.08), this.materiais.escuro);
        pdb.position.set(0.12, yFundo + 0.028, 0);
        this.grupoCaixa.add(pdb);

        // Notebook (carga útil), inicialmente oculto
        this.notebook = new THREE.Group();
        const base = new THREE.Mesh(new THREE.BoxGeometry(0.31, 0.02, 0.22), this.materiais.escuro);
        this.notebook.add(base);
        const tela = new THREE.Mesh(new THREE.BoxGeometry(0.29, 0.001, 0.20), this.materiais.tela);
        tela.position.y = 0.011;
        this.notebook.add(tela);
        this.notebook.position.set(0, yFundo + 0.075, 0);
        this.notebook.visible = false;
        this.grupoCaixa.add(this.notebook);

        // Câmera FPV no topo frontal
        const cam = new THREE.Mesh(new THREE.CylinderGeometry(0.016, 0.016, 0.03, 12),
                                   this.materiais.escuro);
        cam.rotation.x = Math.PI / 2;
        cam.position.set(0, yFundo + altura - 0.04, -profundidade / 2 - 0.015);
        this.grupoCaixa.add(cam);

        // Botão de emergência
        const estop = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.018, 0.012, 16),
                                     new THREE.MeshStandardMaterial({ color: 0xd50000 }));
        estop.position.set(0.14, yFundo + altura + 0.008, 0.1);
        this.grupoCaixa.add(estop);
    }

    // -- braços em V invertido + mangas 4WS + rodas -----------------------
    construirBracos() {
        const raioTubo = 0.014;
        for (const id of IDS_RODAS) {
            const p = POSICOES_RODAS[id];
            const sx = Math.sign(p.x), sz = Math.sign(p.z);
            const braco = new THREE.Group();
            braco.name = `braco_${id}`;

            // Cotas vindas de simulador_python/estrutura.py, via parametros.js:
            // o modelo 3D não tem mais nenhuma cota de braço escrita à mão.
            const g = PARAMETROS.estrutura.bracos[id];
            const emCg = (v) => new THREE.Vector3(v[0], v[1] - V.altura_cg_chassi, v[2]);
            const yEixo = -OFFSET_CG;
            const pAbraca = emCg(g.abracadeira);
            const pVertice = emCg(g.vertice);
            const pManga = emCg(g.manga);

            const abraca = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.06, 0.06), this.materiais.petg);
            abraca.position.copy(pAbraca);
            braco.add(abraca);
            braco.add(tuboEntre(pAbraca, pVertice, raioTubo, this.materiais.pvc));

            const vertice = new THREE.Mesh(new THREE.SphereGeometry(0.034, 14, 12), this.materiais.petg);
            vertice.position.copy(pVertice);
            braco.add(vertice);
            braco.add(tuboEntre(pVertice, pManga, raioTubo, this.materiais.pvc));

            // Manga de esterçamento (gira em torno de Y)
            const manga = new THREE.Group();
            manga.position.set(p.x, yEixo, p.z);

            const corpo = new THREE.Mesh(new THREE.BoxGeometry(0.055, 0.10, 0.055), this.materiais.petg);
            corpo.position.y = 0.05;
            manga.add(corpo);

            const servo = new THREE.Mesh(new THREE.BoxGeometry(0.042, 0.038, 0.048), this.materiais.escuro);
            servo.position.y = 0.115;
            manga.add(servo);

            const motor = new THREE.Mesh(new THREE.CylinderGeometry(0.019, 0.019, 0.058, 14),
                                         this.materiais.escuro);
            motor.rotation.z = Math.PI / 2;
            motor.position.x = sx * 0.022;
            manga.add(motor);

            // Feixe de elásticos: agora com o curso real de projeto
            const feixe = new THREE.Group();
            const n = Math.min(6, PARAMETROS.suspensao_elastica.elasticos_por_perna);
            for (let b = 0; b < n; b++) {
                const el = new THREE.Mesh(
                    new THREE.CylinderGeometry(0.0032, 0.0032, PARAMETROS.suspensao_elastica.curso_maximo * 1.4, 6),
                    this.materiais.elastico,
                );
                const ang = (b / n) * Math.PI * 2;
                el.position.set(Math.cos(ang) * 0.026, 0.06, Math.sin(ang) * 0.026);
                feixe.add(el);
            }
            manga.add(feixe);
            this.elasticos[id] = feixe;

            const { roda, csts } = this.construirRoda(sx);
            roda.position.x = sx * 0.055;
            manga.add(roda);
            this.rodas[id] = roda;
            this.modulosCsts[id] = csts;

            const halo = new THREE.Mesh(
                new THREE.RingGeometry(this.raioMax * 0.18, this.raioMax * 0.36, 18),
                this.materiais.halo.clone());
            halo.rotation.x = -Math.PI / 2;
            halo.position.y = -this.raioMax + 0.005;
            manga.add(halo);
            this.halos[id] = halo;

            braco.add(manga);
            this.mangas[id] = manga;
            this.bracos[id] = braco;
            this.grupo.add(braco);
        }
    }

    construirRoda(sentidoX) {
        const roda = new THREE.Group();
        const rMax = this.raioMax, rCubo = this.raioCubo;

        // Módulo C-STS: espiral plana com a geometria dimensionada
        const csts = new THREE.Group();
        const eixo = new THREE.Mesh(new THREE.CylinderGeometry(0.016, 0.016, 0.03, 14),
                                    this.materiais.petg);
        eixo.rotation.z = Math.PI / 2;
        csts.add(eixo);

        const forma = new THREE.Shape();
        const voltas = CS.comprimento_desenrolado_L /
                       (Math.PI * (CS.raio_interno_espiral + CS.raio_externo_espiral));
        const passosEsp = 48;
        const pts = [];
        for (let i = 0; i <= passosEsp; i++) {
            const t = i / passosEsp;
            const raio = CS.raio_interno_espiral +
                         t * (CS.raio_externo_espiral - CS.raio_interno_espiral);
            const th = t * Math.PI * 2 * voltas * sentidoX;
            pts.push(new THREE.Vector2(Math.cos(th) * raio, Math.sin(th) * raio));
        }
        forma.moveTo(pts[0].x, pts[0].y);
        for (let i = 1; i <= passosEsp; i++) forma.lineTo(pts[i].x, pts[i].y);
        for (let i = passosEsp; i >= 0; i--) {
            const t = i / passosEsp;
            const raio = CS.raio_interno_espiral - CS.espessura_t +
                         t * (CS.raio_externo_espiral - CS.raio_interno_espiral);
            const th = t * Math.PI * 2 * voltas * sentidoX;
            forma.lineTo(Math.cos(th) * raio, Math.sin(th) * raio);
        }
        forma.closePath();
        const espiral = new THREE.Mesh(
            new THREE.ExtrudeGeometry(forma, { depth: CS.largura_b, bevelEnabled: false }),
            this.materiais.csts,
        );
        espiral.rotation.y = Math.PI / 2;
        espiral.position.x = -CS.largura_b / 2;
        csts.add(espiral);

        const anelCubo = new THREE.Mesh(new THREE.TorusGeometry(rCubo, 0.006, 8, 26),
                                        this.materiais.petg);
        anelCubo.rotation.y = Math.PI / 2;
        csts.add(anelCubo);
        roda.add(csts);

        // Raios curvos, gerados pela MESMA parametrização da física
        const perfil = perfilRaios(24, this.raioMax, this.raioCubo);
        const porRaio = perfil.length / R.num_raios_N;
        for (let s = 0; s < R.num_raios_N; s++) {
            const forma2 = new THREE.Shape();
            const trecho = perfil.slice(s * porRaio, (s + 1) * porRaio);
            // Espessura real do raio, afinando da raiz para a ponta (parâmetros mestres)
            const espessura = (u) => R.espessura_raiz + u * (R.espessura_ponta - R.espessura_raiz);
            forma2.moveTo(Math.cos(trecho[0].th) * trecho[0].r, Math.sin(trecho[0].th) * trecho[0].r);
            for (const p of trecho) {
                forma2.lineTo(Math.cos(p.th) * p.r, Math.sin(p.th) * p.r);
            }
            for (let i = trecho.length - 1; i >= 0; i--) {
                const p = trecho[i];
                const rr = p.r - espessura(p.u);
                forma2.lineTo(Math.cos(p.th) * rr, Math.sin(p.th) * rr);
            }
            forma2.closePath();
            const malha = new THREE.Mesh(
                new THREE.ExtrudeGeometry(forma2, { depth: R.largura_raio, bevelEnabled: false }),
                this.materiais.petg,
            );
            malha.rotation.y = Math.PI / 2;
            malha.position.x = -R.largura_raio / 2;
            malha.castShadow = true;
            roda.add(malha);

            // Pastilha de borracha na ponta
            const ponta = trecho[trecho.length - 1];
            const garra = new THREE.Mesh(
                new THREE.BoxGeometry(R.largura_raio + 0.006, 0.012, 0.026),
                this.materiais.aro,
            );
            garra.position.set(0, Math.sin(ponta.th) * ponta.r, Math.cos(ponta.th) * ponta.r);
            roda.add(garra);
        }

        // Aro elástico — item crítico do projeto, representado como um toro fino
        const aro = new THREE.Mesh(
            new THREE.TorusGeometry(rMax - 0.009, 0.009, 10, 44),
            this.materiais.aro,
        );
        aro.rotation.y = Math.PI / 2;
        aro.name = 'aro';
        roda.add(aro);
        this._aroVisivel = true;

        return { roda, csts };
    }

    // -- atualização a cada quadro ---------------------------------------
    aplicarEstado(fisica) {
        for (const id of IDS_RODAS) {
            const manga = this.mangas[id];
            if (!manga) continue;
            manga.rotation.y = fisica.anguloEstercamento[id] || 0;

            // curso real da suspensão: cota da roda em relação ao ponto de fixação
            const p = POSICOES_RODAS[id];
            const alavancaArf = -p.z, alavancaRol = p.x;
            const yFixacao = fisica.y - OFFSET_CG
                + alavancaArf * Math.sin(fisica.arfagem)
                + alavancaRol * Math.sin(fisica.rolagem);
            const curso = fisica.rodas[id].altura - yFixacao;
            manga.position.y = -OFFSET_CG + Math.max(-0.12, Math.min(0.12, curso));

            this.rodas[id].rotation.x = -fisica.rodas[id].psi;
            this.modulosCsts[id].rotation.x = fisica.rodas[id].deflexaoCsts;

            const escala = 1 + Math.max(-0.4, Math.min(0.4, -curso / 0.09)) * 0.35;
            this.elasticos[id].scale.set(1, escala, 1);

            const halo = this.halos[id];
            halo.visible = fisica.rodas[id].emContato;
            halo.material.opacity = Math.min(0.85, 0.15 + fisica.forcasNormais[id] / 60);
            halo.material.color.setHex(
                fisica.rodas[id].tipoContato === 'raio' ? 0xffa000 : 0x00e5ff);
        }
        this.grupoCaixa.rotation.x = fisica.pendulo - fisica.arfagem;
    }

    definirAroVisivel(visivel) {
        this._aroVisivel = visivel;
        for (const id of IDS_RODAS) {
            this.rodas[id].traverse((o) => { if (o.name === 'aro') o.visible = visivel; });
        }
    }

    carregarNotebook(estado) { this.notebook.visible = estado; }

    alternarTampa() {
        this.tampaAberta = !this.tampaAberta;
        this.tampa.rotation.x = this.tampaAberta ? -2.0 : 0;
        return this.tampaAberta;
    }

    alternarExplodido() {
        this.explodido = !this.explodido;
        const d = this.explodido ? 0.16 : 0;
        for (const id of IDS_RODAS) {
            const p = POSICOES_RODAS[id];
            this.bracos[id].position.set(Math.sign(p.x) * d, d * 0.4, Math.sign(p.z) * d);
        }
        this.grupoCaixa.position.y = this.explodido ? -0.10 : 0;
        return this.explodido;
    }
}
