// =============================================================================
//  APLICAÇÃO — Gêmeo digital do Rover Frugal no percurso do Itaipu Parquetec
// =============================================================================

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { PARAMETROS, IDS_RODAS } from './parametros.js';
import { FisicaRover } from './fisica.js';
import { ModeloRover } from './rover_model.js';
import { Terreno } from './terreno.js';

const RAD = 180 / Math.PI;

// -----------------------------------------------------------------------------
// Cena
// -----------------------------------------------------------------------------
const container = document.getElementById('canvas-container');
const cena = new THREE.Scene();
cena.background = new THREE.Color(0x0a0e16);
cena.fog = new THREE.FogExp2(0x0a0e16, 0.018);

const camera = new THREE.PerspectiveCamera(52, window.innerWidth / window.innerHeight, 0.05, 300);
camera.position.set(2.6, 2.0, 3.0);

const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.15;
container.appendChild(renderer.domElement);

const controles = new OrbitControls(camera, renderer.domElement);
controles.enableDamping = true;
controles.dampingFactor = 0.06;
controles.maxPolarAngle = Math.PI / 2 - 0.03;
controles.minDistance = 0.9;
controles.maxDistance = 30;

cena.add(new THREE.AmbientLight(0xffffff, 0.7));
const sol = new THREE.DirectionalLight(0xfff2e0, 2.0);
sol.position.set(8, 14, 6);
sol.castShadow = true;
sol.shadow.mapSize.set(2048, 2048);
sol.shadow.camera.left = -25; sol.shadow.camera.right = 25;
sol.shadow.camera.top = 25; sol.shadow.camera.bottom = -25;
sol.shadow.camera.far = 60;
cena.add(sol);
const luzFria = new THREE.DirectionalLight(0x2b6f86, 0.5);
luzFria.position.set(-6, 4, -8);
cena.add(luzFria);

const terreno = new Terreno();
cena.add(terreno.grupo);

let fisica = new FisicaRover();
let modelo = new ModeloRover();
cena.add(modelo.grupo);

// -----------------------------------------------------------------------------
// Estado da aplicação
// -----------------------------------------------------------------------------
const estado = {
    modo: 'ackermann',
    camera: 'orbita',
    teclas: {},
    parado: false,
    aceleracao: 0,
    esterco: 0,
    tempoMissao: 0,
    faseMissao: 'ida',        // ida -> coleta -> retorno -> entregue
    comCarga: false,
    gravando: false,
    telemetria: [],
    variante: 'v2',           // 'v1' = roda Φ300 legada, para comparação
    ultimoAviso: '',
};

function reiniciarRover(opcoes = {}) {
    cena.remove(modelo.grupo);
    if (estado.variante === 'v1') {
        opcoes = { ...opcoes, raioMax: 0.150, raioCubo: 0.045 };
    }
    fisica = new FisicaRover(opcoes);
    modelo = new ModeloRover({ raioMax: fisica.raioMax, raioCubo: fisica.raioCubo });
    cena.add(modelo.grupo);
    fisica.reiniciar(terreno.pontoBase.x, terreno.pontoBase.z, 0);
    estado.tempoMissao = 0;
    estado.faseMissao = 'ida';
    estado.comCarga = false;
    estado.telemetria = [];
    modelo.definirAroVisivel(fisica.opcoes.comAro);
}
fisica.reiniciar(terreno.pontoBase.x, terreno.pontoBase.z, 0);

// -----------------------------------------------------------------------------
// Entrada
// -----------------------------------------------------------------------------
window.addEventListener('keydown', (e) => {
    estado.teclas[e.key.toLowerCase()] = true;
    if (e.key === ' ') e.preventDefault();
});
window.addEventListener('keyup', (e) => { estado.teclas[e.key.toLowerCase()] = false; });

function ligar(id, fn) {
    const el = document.getElementById(id);
    if (el) el.addEventListener('click', fn);
}

document.querySelectorAll('.btn-mode').forEach((btn) => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.btn-mode').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        estado.modo = btn.dataset.mode;
        avisar(`Modo ${btn.dataset.mode}: reconfigurando servos ` +
               `(δs = 2 exige parar para reorientar)`);
    });
});

document.querySelectorAll('.btn-cam').forEach((btn) => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.btn-cam').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        estado.camera = btn.dataset.cam;
        controles.enabled = estado.camera === 'orbita';
    });
});

document.querySelectorAll('[data-toggle]').forEach((el) => {
    el.addEventListener('change', () => {
        const opcoes = {
            comAro: document.getElementById('sw-aro').checked,
            comCsts: document.getElementById('sw-csts').checked,
            comElasticos: document.getElementById('sw-elasticos').checked,
        };
        reiniciarRover(opcoes);
        avisar('Configuração de suspensão alterada — rover reposicionado na base.');
    });
});

ligar('btn-tampa', () => modelo.alternarTampa());
ligar('btn-explodir', () => modelo.alternarExplodido());
ligar('btn-reiniciar', () => reiniciarRover(fisica.opcoes));
ligar('btn-escada', () => {
    const z = terreno.pontoColeta.z - 1.5;
    fisica.reiniciar(0, z, 0);
    estado.modo = 'stair';
    document.querySelectorAll('.btn-mode').forEach((b) => b.classList.remove('active'));
    document.querySelector('[data-mode="stair"]')?.classList.add('active');
    avisar('Posicionado ao pé da escadaria em modo escada.');
});
ligar('btn-estop', () => {
    estado.parado = !estado.parado;
    const btn = document.getElementById('btn-estop');
    btn.textContent = estado.parado ? '⚡ Rearmar sistema' : '🛑 Parada de emergência';
    btn.classList.toggle('armado', estado.parado);
});
ligar('btn-csv', exportarCsv);
ligar('btn-variante', () => {
    estado.variante = estado.variante === 'v2' ? 'v1' : 'v2';
    avisar(estado.variante === 'v1'
        ? 'Comparação: roda Φ300 do projeto original — alcance nariz-a-nariz de 260 mm '
          + 'contra 345 mm exigidos. Ela trava na face do espelho.'
        : 'De volta à roda Φ420 dimensionada por marcha síncrona.');
    document.getElementById('btn-variante').textContent =
        estado.variante === 'v2' ? '🔬 Comparar com a roda Φ300 (R1)' : '↩︎ Voltar à roda Φ420 (R2)';
    aplicarVariante();
});

/** Reconstrói o rover com o raio da variante escolhida — física inclusive. */
function aplicarVariante() {
    reiniciarRover({
        comAro: document.getElementById('sw-aro').checked,
        comCsts: document.getElementById('sw-csts').checked,
        comElasticos: document.getElementById('sw-elasticos').checked,
    });
    texto('badge-roda', `Φ${(2 * fisica.raioMax * 1000).toFixed(0)} mm · ${PARAMETROS.roda.num_raios_N} raios`);
    const el = document.getElementById('badge-sincrona');
    if (el) {
        el.textContent = fisica.marchaSincrona ? 'marcha síncrona ✔' : 'marcha assíncrona ✘';
        el.classList.toggle('ruim', !fisica.marchaSincrona);
    }
}

const dpad = (id, tecla) => {
    const el = document.getElementById(id);
    if (!el) return;
    const on = (e) => { e.preventDefault(); estado.teclas[tecla] = true; };
    const off = (e) => { e.preventDefault(); estado.teclas[tecla] = false; };
    el.addEventListener('mousedown', on); el.addEventListener('mouseup', off);
    el.addEventListener('mouseleave', off);
    el.addEventListener('touchstart', on); el.addEventListener('touchend', off);
};
dpad('dpad-up', 'w'); dpad('dpad-down', 's');
dpad('dpad-left', 'a'); dpad('dpad-right', 'd');

function avisar(texto) {
    estado.ultimoAviso = texto;
    const el = document.getElementById('faixa-aviso');
    if (!el) return;
    el.textContent = texto;
    el.classList.add('visivel');
    clearTimeout(avisar._t);
    avisar._t = setTimeout(() => el.classList.remove('visivel'), 5200);
}

// -----------------------------------------------------------------------------
// Missão
// -----------------------------------------------------------------------------
function atualizarMissao() {
    const pos = new THREE.Vector3(fisica.x, 0, fisica.z);
    const dColeta = pos.distanceTo(new THREE.Vector3(terreno.pontoColeta.x, 0, terreno.pontoColeta.z));
    const dEntrega = pos.distanceTo(new THREE.Vector3(terreno.pontoEntrega.x, 0, terreno.pontoEntrega.z));

    if (estado.faseMissao === 'ida' && dColeta < 0.9 && Math.abs(fisica.velocidade) < 0.15) {
        estado.faseMissao = 'retorno';
        estado.comCarga = true;
        modelo.carregarNotebook(true);
        avisar('📦 Notebook embarcado. Leve-o até a T.I. no topo da escadaria.');
    } else if (estado.faseMissao === 'retorno' && dEntrega < 0.9 && Math.abs(fisica.velocidade) < 0.15) {
        estado.faseMissao = 'entregue';
        modelo.carregarNotebook(false);
        avisar(`✅ Missão cumprida em ${estado.tempoMissao.toFixed(0)} s. `
             + `Pico na carga: ${fisica.picoCargaG.toFixed(2)} g `
             + `(limite ${PARAMETROS.controle.limite_choque_carga_g} g). `
             + `Energia: ${fisica.bateria.consumidoWh.toFixed(1)} Wh.`);
    }
}

function exportarCsv() {
    if (estado.telemetria.length === 0) { avisar('Sem telemetria gravada ainda.'); return; }
    const chaves = Object.keys(estado.telemetria[0]);
    const linhas = [chaves.join(',')];
    for (const l of estado.telemetria) {
        linhas.push(chaves.map((k) => (typeof l[k] === 'number' ? l[k].toFixed(5) : l[k])).join(','));
    }
    const blob = new Blob([linhas.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'telemetria_rover.csv';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
    avisar(`Telemetria exportada (${estado.telemetria.length} amostras).`);
}

// -----------------------------------------------------------------------------
// HUD
// -----------------------------------------------------------------------------
const el = (id) => document.getElementById(id);
function texto(id, valor) { const e = el(id); if (e) e.innerHTML = valor; }
function barra(id, fracao, critico = false) {
    const e = el(id);
    if (!e) return;
    e.style.width = `${Math.max(0, Math.min(100, fracao * 100))}%`;
    e.classList.toggle('critico', critico);
}

function atualizarHud() {
    const v = Math.abs(fisica.velocidade);
    texto('val-speed', `${v.toFixed(2)} <small>m/s</small>`);
    barra('bar-speed', v / PARAMETROS.cinematica.velocidade_maxima);

    const cargaG = Math.abs(fisica.aceleracaoCarga.vertical);
    const limite = PARAMETROS.controle.limite_choque_carga_g;
    texto('val-carga', `${cargaG.toFixed(2)} <small>g</small>`);
    barra('bar-carga', cargaG / limite, cargaG > limite);
    texto('val-carga-pico', `${fisica.picoCargaG.toFixed(2)} g`);

    texto('val-pitch', `${(fisica.arfagem * RAD).toFixed(1)}°`);
    texto('val-roll', `${(fisica.rolagem * RAD).toFixed(1)}°`);
    texto('val-limiar', `${fisica.limiarArfagem.toFixed(0)}°`);
    const horizonte = el('horizon-disc');
    if (horizonte) {
        horizonte.style.transform =
            `rotate(${-fisica.rolagem * RAD}deg) translateY(${fisica.arfagem * RAD * 1.6}px)`;
    }

    for (const id of IDS_RODAS) {
        texto(`val-steer-${id.toLowerCase()}`, `${(fisica.anguloEstercamento[id] * RAD).toFixed(0)}°`);
        texto(`fz-${id.toLowerCase()}`, `${fisica.forcasNormais[id].toFixed(1)} N`);
        const r = fisica.rodas[id];
        texto(`contato-${id.toLowerCase()}`, r.tipoContato === 'raio' ? 'raio' : 'aro');
        texto(`csts-${id.toLowerCase()}`, `${(r.deflexaoCsts * RAD).toFixed(0)}°`);
    }

    texto('val-soc', `${(fisica.bateria.soc * 100).toFixed(0)} <small>%</small>`);
    barra('bar-soc', fisica.bateria.soc, fisica.bateria.soc < 0.25);
    texto('val-corrente', `${fisica.correnteTotal.toFixed(1)} <small>A</small>`);
    texto('val-tensao', `${fisica.bateria.tensao(fisica.correnteTotal).toFixed(1)} V`);
    texto('val-wh', `${fisica.bateria.consumidoWh.toFixed(2)} Wh`);

    texto('val-temp', `${fisica.termica.temperatura.toFixed(0)} <small>°C</small>`);
    barra('bar-temp', fisica.termica.fracao, fisica.termica.fracao > 0.85);

    texto('val-margem', fisica.margemTorque > 90 ? '—' : fisica.margemTorque.toFixed(2));
    texto('val-torque', `${fisica.torquePorRoda.toFixed(2)} N·m`);
    texto('val-dist', `${fisica.distanciaPercorrida.toFixed(1)} m`);
    texto('val-tempo', `${estado.tempoMissao.toFixed(0)} s`);

    const fases = { ida: 'Ida — buscar o notebook', retorno: 'Retorno — entregar na T.I.',
                    entregue: 'Missão concluída' };
    texto('val-fase', fases[estado.faseMissao]);

    const alertas = [];
    if (fisica.alertaTombamento) alertas.push('⚠️ INCLINAÇÃO CRÍTICA');
    if (fisica.emProtecaoTermica) alertas.push('🌡️ PROTEÇÃO TÉRMICA (I²t)');
    if (fisica.escorregando) alertas.push('🧊 ATRITO INSUFICIENTE');
    if (fisica.margemTorque < 1.0) alertas.push('🔧 TORQUE SATURADO');
    if (fisica.estercamentoSaturado) alertas.push('🔄 ESTERÇAMENTO SATURADO (odometria degradada)');
    if (cargaG > limite) alertas.push('📦 CHOQUE ACIMA DO LIMITE DA CARGA');
    const caixaAlertas = el('painel-alertas');
    if (caixaAlertas) {
        caixaAlertas.innerHTML = alertas.length
            ? alertas.map((a) => `<div class="alerta">${a}</div>`).join('')
            : '<div class="alerta ok">✔ Todos os parâmetros dentro do envelope</div>';
    }
}

// -----------------------------------------------------------------------------
// Laço principal
// -----------------------------------------------------------------------------
let ultimoTempo = performance.now();
let acumuladorTelemetria = 0;

function animar(agora) {
    requestAnimationFrame(animar);
    const dt = Math.min((agora - ultimoTempo) / 1000, 0.05);
    ultimoTempo = agora;

    const t = estado.teclas;
    const frente = (t.w || t.arrowup) ? 1 : (t.s || t.arrowdown) ? -1 : 0;
    const lado = (t.a || t.arrowleft) ? 1 : (t.d || t.arrowright) ? -1 : 0;

    const vMax = estado.modo === 'stair'
        ? PARAMETROS.cinematica.velocidade_escada
        : PARAMETROS.cinematica.velocidade_maxima;

    let velocidadeAlvo = estado.parado ? 0 : frente * vMax;
    if (t[' ']) velocidadeAlvo = 0;

    const comando = {
        modo: estado.modo,
        velocidadeAlvo,
        vFrente: velocidadeAlvo,
        vLateral: estado.modo === 'crab' ? lado * vMax * 0.8 : 0,
        omega: estado.modo === 'spin' ? lado * 1.2 : lado * 0.9,
    };

    fisica.avancar(terreno, comando, dt);
    modelo.aplicarEstado(fisica);

    modelo.grupo.position.set(fisica.x, fisica.y, fisica.z);
    modelo.grupo.rotation.set(fisica.arfagem, fisica.rumo, fisica.rolagem, 'YXZ');

    // O cronômetro da missão segue o TEMPO SIMULADO, não o relógio de parede:
    // em máquina lenta (ou sem GPU) a física roda em câmera lenta, e misturar as
    // duas bases faria a telemetria mentir sobre velocidade e energia.
    if (estado.faseMissao !== 'entregue') estado.tempoMissao = fisica.tempo;
    atualizarMissao();

    acumuladorTelemetria += dt;
    if (acumuladorTelemetria >= 1 / PARAMETROS.controle.frequencia_telemetria_hz) {
        acumuladorTelemetria = 0;
        estado.telemetria.push(fisica.telemetria());
        if (estado.telemetria.length > 20000) estado.telemetria.shift();
    }

    atualizarCamera();
    atualizarHud();
    if (estado.camera === 'orbita') controles.update();
    renderer.render(cena, camera);
}

function atualizarCamera() {
    const pos = new THREE.Vector3(fisica.x, fisica.y, fisica.z);
    if (estado.camera === 'orbita') {
        controles.target.lerp(pos, 0.15);
    } else if (estado.camera === 'fpv') {
        const offset = new THREE.Vector3(0, 0.22, -0.26)
            .applyAxisAngle(new THREE.Vector3(0, 1, 0), fisica.rumo);
        camera.position.copy(pos.clone().add(offset));
        const alvo = new THREE.Vector3(0, 0.05, -3.0)
            .applyAxisAngle(new THREE.Vector3(0, 1, 0), fisica.rumo).add(pos);
        camera.lookAt(alvo);
    } else if (estado.camera === 'topo') {
        camera.position.set(fisica.x, fisica.y + 6.0, fisica.z + 0.01);
        camera.lookAt(fisica.x, fisica.y, fisica.z);
    } else if (estado.camera === 'lateral') {
        const lado = new THREE.Vector3(2.6, 0.5, 0)
            .applyAxisAngle(new THREE.Vector3(0, 1, 0), fisica.rumo);
        camera.position.copy(pos.clone().add(lado));
        camera.lookAt(pos);
    }
}

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

// Cabeçalho com os parâmetros ativos — o protótipo declara o que está simulando
texto('badge-roda', `Φ${(2 * PARAMETROS.roda.raio_max * 1000).toFixed(0)} mm · ${PARAMETROS.roda.num_raios_N} raios`);
texto('badge-massa', `${PARAMETROS.massas.massa_total.toFixed(1)} kg`);
texto('badge-escada', `degrau ${(PARAMETROS.ambiente.escada.espelho_E * 1000).toFixed(0)}×${(PARAMETROS.ambiente.escada.piso_P * 1000).toFixed(0)} mm`);
texto('badge-revisao', PARAMETROS.meta.revisao);

avisar('Percurso de homologação carregado. Vá até o marcador azul, embarque o notebook '
     + 'e entregue no marcador verde, no topo da escadaria.');
requestAnimationFrame(animar);
