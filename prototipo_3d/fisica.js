// =============================================================================
//  FÍSICA DO ROVER — versão em tempo real do modelo de `simulador_python/`
//
//  O simulador anterior movia a carroceria por interpolação exponencial em
//  direção a `terreno + 0,15`, ou seja: a roda era tratada como um DISCO de raio
//  fixo. Toda a mecânica que o projeto defende (raios curvos, transferência
//  CCS/DCS, C-STS, aro elástico) era puramente decorativa.
//
//  Aqui a cadeia é a mesma do Python:
//    1. contato real dos raios curvos com o terreno, roda a roda;
//    2. aro elástico como piso de contato contínuo;
//    3. suspensão elástica com curso e batente;
//    4. C-STS torsional integrada, com energia armazenada;
//    5. motor com curva torque-velocidade, corrente, bateria e temperatura.
// =============================================================================

import { PARAMETROS, POSICOES_RODAS, IDS_RODAS } from './parametros.js';

const G = 9.80665;
const R = PARAMETROS.roda;
const V = PARAMETROS.veiculo;
const SUS = PARAMETROS.suspensao_elastica;
const ARO = PARAMETROS.aro_elastico;
const PW = PARAMETROS.powertrain;
const EN = PARAMETROS.energia;

// -----------------------------------------------------------------------------
// 1. PERFIL DA RODA DE RAIOS CURVOS (mesma parametrização do Python)
// -----------------------------------------------------------------------------
export function perfilRaios(amostras = 26, raioMax = R.raio_max, raioCubo = R.raio_cubo) {
    const pontos = [];
    for (let s = 0; s < R.num_raios_N; s++) {
        const base = (s * 2 * Math.PI) / R.num_raios_N;
        for (let i = 0; i < amostras; i++) {
            const u = i / (amostras - 1);
            const raio = raioCubo + u * (raioMax - raioCubo);
            const th = base + R.sentido_curvatura * R.varredura_rad * Math.pow(u, R.expoente_perfil);
            pontos.push({ r: raio, th, u });
        }
    }
    return pontos;
}

/** Alcance nariz-a-nariz: 2·r_max·sin(π/N) — a condição de marcha síncrona. */
export function alcanceNarizANariz(raioMax = R.raio_max) {
    return 2 * raioMax * Math.sin(Math.PI / R.num_raios_N);
}

// -----------------------------------------------------------------------------
// 2. MOTOR, BATERIA E TÉRMICA
// -----------------------------------------------------------------------------
export class Motor {
    constructor() {
        this.kt = 60.0 / (2 * Math.PI * PW.motor.kv_rpm_por_volt);
        this.reducao = PW.reducao;
        this.eta = PW.eficiencia_reducao;
        this.ra = PW.motor.resistencia_armadura;
        this.i0 = PW.motor.corrente_vazio;
        this.limite = PW.limite_corrente_driver;
    }

    /** Torque disponível no eixo de saída e corrente, para uma rotação imposta. */
    ponto(omegaSaida, tensao) {
        const fcem = this.kt * Math.abs(omegaSaida) * this.reducao;
        let corrente = Math.max(0, (tensao - fcem) / this.ra);
        corrente = Math.min(corrente, this.limite);
        const torque = this.kt * Math.max(0, corrente - this.i0) * this.reducao * this.eta;
        return { torque, corrente };
    }

    correnteParaTorque(torqueSaida) {
        return Math.abs(torqueSaida) / (this.reducao * this.eta) / this.kt + this.i0;
    }
}

export class Bateria {
    constructor() {
        this.capacidadeAh = EN.celulas_paralelo * EN.capacidade_celula_ah;
        this.rInterna = (EN.resistencia_interna_celula * EN.celulas_serie) / EN.celulas_paralelo;
        this.energiaWh = this.capacidadeAh * EN.celulas_serie * EN.tensao_nominal_celula;
        this.soc = 1.0;
        this.consumidoWh = 0.0;
    }

    tensao(corrente) {
        const ocv = EN.tensao_corte_celula
            + (EN.tensao_cheia_celula - EN.tensao_corte_celula) * (0.15 + 0.85 * this.soc);
        return Math.max(EN.celulas_serie * EN.tensao_corte_celula,
                        EN.celulas_serie * ocv - corrente * this.rInterna);
    }

    consumir(potenciaW, dt) {
        this.consumidoWh += (potenciaW * dt) / 3600.0;
        this.soc = Math.max(0, 1 - this.consumidoWh / this.energiaWh);
    }

    get autonomiaRestanteMin() {
        return this.soc * this.energiaWh * (1 - EN.reserva_operacional);
    }
}

export class Termica {
    constructor() {
        this.rTermica = 8.0; this.cTermica = 30.0;
        this.ambiente = 35.0; this.maxima = 115.0;
        this.temperatura = this.ambiente;
    }
    passo(corrente, dt) {
        const p = corrente * corrente * PW.motor.resistencia_armadura;
        const regime = this.ambiente + p * this.rTermica;
        const tau = this.rTermica * this.cTermica;
        this.temperatura += ((regime - this.temperatura) / tau) * dt;
        return this.temperatura;
    }
    get fracao() { return (this.temperatura - this.ambiente) / (this.maxima - this.ambiente); }
    get emProtecao() { return this.temperatura >= this.maxima; }
}

// -----------------------------------------------------------------------------
// 3. RODA — massa não suspensa com contato de raio curvo + aro elástico + C-STS
// -----------------------------------------------------------------------------
export class Roda {
    constructor(id, opcoes = {}) {
        this.id = id;
        this.comAro = opcoes.comAro !== false;
        this.comCsts = opcoes.comCsts !== false;
        this.raioMax = opcoes.raioMax || R.raio_max;
        this.raioCubo = opcoes.raioCubo || R.raio_cubo;
        this.perfil = perfilRaios(26, this.raioMax, this.raioCubo);
        this.massa = PARAMETROS.massas.rodas_conjunto / 4;

        this.psi = Math.random() * 2 * Math.PI;   // fase de chegada não é controlável
        this.altura = this.raioMax;
        this.velocidade = 0.0;
        this.deflexaoCsts = 0.0;
        this.omegaRoda = 0.0;
        this.raioEfetivo = this.raioMax;
        this.emContato = true;
        this.forcaNormal = V.peso_total_N / 4;
        this.forcaContato = 0.0;
        this.tipoContato = 'aro';
        this.faseRaio = 0.0;
        this.alturaAlvo = this.raioMax;
    }

    /**
     * Cota mínima do cubo para que nenhum ponto de raio penetre o terreno.
     * É a mesma operação de assentamento de `SimuladorMarcha._assentar`, só que
     * resolvida a cada quadro em vez de por eventos.
     */
    assentar(terreno, x, z, direcao) {
        let necessaria = -Infinity;
        let raioNoContato = this.raioMax;
        for (const p of this.perfil) {
            const ang = p.th - this.psi;              // giro horário = avanço
            const dx = p.r * Math.cos(ang);
            const dy = p.r * Math.sin(ang);
            const yTerreno = terreno.alturaEm(x + direcao.x * dx, z + direcao.z * dx);
            const candidato = yTerreno - dy;
            if (candidato > necessaria) { necessaria = candidato; raioNoContato = p.r; }
        }
        this.raioEfetivo = raioNoContato;
        return necessaria;
    }

    /**
     * Alvo de contato: o maior entre o apoio nos raios e o piso do aro elástico.
     *
     * O assentamento puro (levantar a roda até não penetrar, com x fixo) é
     * DESCONTÍNUO onde o terreno é — ao cruzar o nariz de um degrau ele salta.
     * O movimento real não salta: a roda PIVOTA em torno do contato corrente, e
     * o cubo desce por um arco de raio r <= r_max, ou seja a |dy/dt| <= omega*r,
     * que é a própria velocidade de avanço. Limitar a taxa de descida reproduz o
     * pivotamento sem precisar resolver eventos a cada quadro — é o que mantém
     * este modelo coerente com `geometria_escada.SimuladorMarcha`.
     */
    atualizarAlvo(terreno, x, z, direcao, velocidadeVeiculo, dt) {
        const porRaios = this.assentar(terreno, x, z, direcao);
        let porAro = -Infinity;
        if (this.comAro) {
            const deflexao = Math.min(this.forcaNormal / ARO.rigidez_radial, ARO.curso_colapso);
            porAro = terreno.alturaEm(x, z) + this.raioMax - deflexao;
        }
        this.tipoContato = porAro >= porRaios ? 'aro' : 'raio';
        const bruto = Math.max(porRaios, porAro);

        // Limite simétrico: subir ou descer, o cubo percorre um arco de raio
        // r <= r_max em torno do contato, logo |dy/dt| <= omega*r_max, e como
        // omega = v/r_contato com r_contato >= r_cubo, o limite é
        // v * (r_max / r_cubo). Aplica-se folga para não travar o assentamento.
        const taxaMax = Math.abs(velocidadeVeiculo) * (this.raioMax / this.raioCubo) + 0.05;
        const piso = this.alturaAlvo - taxaMax * dt;
        const teto = this.alturaAlvo + taxaMax * dt;
        this.alturaAlvo = Math.min(teto, Math.max(bruto, piso));
        return this.alturaAlvo;
    }

    /** Integra a massa não suspensa: contato para cima, suspensão e peso para baixo. */
    integrar(forcaSuspensao, dt) {
        const kContato = this.comAro ? ARO.rigidez_radial : 5.0e4;
        const penetracao = this.alturaAlvo - this.altura;
        this.forcaContato = penetracao > 0
            ? kContato * penetracao + 60.0 * Math.max(0, -this.velocidade)
            : 0.0;
        this.emContato = penetracao > -0.003;

        const acel = (this.forcaContato - forcaSuspensao) / this.massa - G;
        this.velocidade += acel * dt;
        this.altura += this.velocidade * dt;
        if (this.altura < this.alturaAlvo - 0.12) {   // guarda contra penetração grosseira
            this.altura = this.alturaAlvo - 0.12;
            this.velocidade = Math.max(this.velocidade, 0);
        }
    }

    /** Dinâmica torsional do C-STS e giro da roda. */
    girar(velocidadeVeiculo, dt) {
        const omegaMotor = velocidadeVeiculo / Math.max(this.raioEfetivo, this.raioCubo);
        if (this.comCsts) {
            const kt = PARAMETROS.csts.kt_projeto;
            const ct = PARAMETROS.csts.amortecimento_ct;
            const inercia = PARAMETROS.csts.inercia_roda;
            const limite = (PARAMETROS.csts.deflexao_maxima_deg * Math.PI) / 180;
            // Torque resistente: braço horizontal do contato x carga normal
            const torqueResistente = this.forcaNormal * this.raioEfetivo * 0.30;
            const d = Math.max(-limite, Math.min(limite, this.deflexaoCsts));
            const batente = Math.abs(this.deflexaoCsts) > limite
                ? 400.0 * (Math.abs(this.deflexaoCsts) - limite) * Math.sign(this.deflexaoCsts)
                : 0.0;
            const tMola = kt * d + batente + ct * (omegaMotor - this.omegaRoda);
            this.omegaRoda += ((tMola - torqueResistente) / inercia) * dt;
            this.omegaRoda = Math.max(-25, Math.min(25, this.omegaRoda));
            this.deflexaoCsts += (omegaMotor - this.omegaRoda) * dt;
            this.deflexaoCsts = Math.max(-1.5 * limite, Math.min(1.5 * limite, this.deflexaoCsts));
        } else {
            this.omegaRoda = omegaMotor;
            this.deflexaoCsts = 0.0;
        }
        this.psi += this.omegaRoda * dt;
        const setor = (2 * Math.PI) / R.num_raios_N;
        this.faseRaio = (((this.psi % setor) + setor) % setor) / setor;
    }

    get energiaCsts() {
        return 0.5 * PARAMETROS.csts.kt_projeto * this.deflexaoCsts * this.deflexaoCsts;
    }
}

// -----------------------------------------------------------------------------
// 4. VEÍCULO COMPLETO — 7 GDL (altura, arfagem, rolagem + 4 massas não suspensas)
// -----------------------------------------------------------------------------
export const DT_FIXO = 1 / 480;      // passo fixo da física, independente do FPS

/**
 * Distância vertical do EIXO das rodas ao CG do veículo.
 * `altura_cg_chassi` é medida a partir do SOLO (é assim que ela é definida no
 * arquivo mestre); o plano de fixação da suspensão fica na cota do eixo. Tratar
 * uma como a outra deslocava o veículo inteiro em r_max.
 */
export const OFFSET_CG = V.altura_cg_chassi - R.raio_max;

export class FisicaRover {
    constructor(opcoes = {}) {
        this.opcoes = {
            comAro: opcoes.comAro !== false,
            comCsts: opcoes.comCsts !== false,
            comElasticos: opcoes.comElasticos !== false,
            raioMax: opcoes.raioMax || R.raio_max,
            raioCubo: opcoes.raioCubo || R.raio_cubo,
        };
        this.raioMax = this.opcoes.raioMax;
        this.raioCubo = this.opcoes.raioCubo;
        this.rodas = {};
        for (const id of IDS_RODAS) this.rodas[id] = new Roda(id, this.opcoes);

        this.motor = new Motor();
        this.bateria = new Bateria();
        this.termica = new Termica();
        this.reiniciar();
    }

    get kSuspensao() { return this.opcoes.comElasticos ? SUS.rigidez_por_roda : 6.0e4; }
    get cSuspensao() { return this.opcoes.comElasticos ? SUS.amortecimento_por_roda : 30.0; }
    get afundamentoEstatico() {
        return PARAMETROS.massas.massa_total * G / (4 * this.kSuspensao);
    }

    reiniciar(x = 0, z = 0, rumo = 0) {
        this.x = x; this.z = z; this.rumo = rumo;
        this.y = this.raioMax + OFFSET_CG;
        this.velY = 0;
        this.arfagem = 0; this.velArfagem = 0;
        this.rolagem = 0; this.velRolagem = 0;
        this.velocidade = 0;
        this.pendulo = 0; this.velPendulo = 0;
        this.tempo = 0;
        this.distanciaPercorrida = 0;
        this.picoCargaG = 0;
        this.correnteTotal = 0;
        this.torquePorRoda = 0;
        this.margemTorque = Infinity;
        this.escorregando = false;
        this.emProtecaoTermica = false;
        this.estercamentoSaturado = false;
        this.modoEscada = false;
        this.aceleracaoCarga = { vertical: 0, longitudinal: 0 };
        this.anguloEstercamento = { FL: 0, FR: 0, RL: 0, RR: 0 };
        this.forcasNormais = { FL: 0, FR: 0, RL: 0, RR: 0 };
        for (const id of IDS_RODAS) {
            const r = this.rodas[id];
            r.altura = this.raioMax; r.velocidade = 0; r.deflexaoCsts = 0;
        }
        this._acumulador = 0;
    }

    /** Cinemática inversa 4WS — mesma formulação de simulador_python/kinematics.py */
    cinematicaInversa(vFrente, vLateral, omega, modo) {
        if (modo === 'stair') { vLateral = 0; omega = 0; }
        if (modo === 'crab') omega = 0;
        if (modo === 'spin') { vFrente = 0; vLateral = 0; }

        const limite = (PARAMETROS.estercamento.angulo_maximo_deg * Math.PI) / 180;
        const angulos = {}; const velocidades = {}; let saturado = false;
        for (const id of IDS_RODAS) {
            const p = POSICOES_RODAS[id];
            const xf = -p.z, ye = -p.x;      // cena -> referencial canônico
            const vix = vFrente - omega * ye;
            const viy = vLateral + omega * xf;
            const modulo = Math.hypot(vix, viy);
            let beta = 0, v = 0;
            if (modulo > 1e-9) {
                beta = Math.atan2(viy, vix);
                v = modulo;
                if (beta > Math.PI / 2) { beta -= Math.PI; v = -modulo; }
                else if (beta < -Math.PI / 2) { beta += Math.PI; v = -modulo; }
                if (Math.abs(beta) > limite) { saturado = true; beta = Math.sign(beta) * limite; }
            }
            angulos[id] = beta; velocidades[id] = v;
        }
        return { angulos, velocidades, saturado };
    }

    /** Avança `dtQuadro` segundos em passos fixos (estabilidade independe do FPS). */
    avancar(terreno, comando, dtQuadro) {
        this._acumulador += Math.min(dtQuadro, 0.05);
        let passos = 0;
        while (this._acumulador >= DT_FIXO && passos < 48) {
            this.passo(terreno, comando, DT_FIXO);
            this._acumulador -= DT_FIXO;
            passos++;
        }
    }

    passo(terreno, comando, dt) {
        this.tempo += dt;
        this.modoEscada = comando.modo === 'stair';

        // --- 1. cinemática 4WS ----------------------------------------------
        const cmd = this.cinematicaInversa(comando.vFrente, comando.vLateral,
                                           comando.omega, comando.modo);
        this.anguloEstercamento = cmd.angulos;
        this.estercamentoSaturado = cmd.saturado;

        // --- 2. limite de torque, corrente e temperatura ----------------------
        const raioEfMedio = IDS_RODAS.reduce((a, id) => a + this.rodas[id].raioEfetivo, 0) / 4;
        const subida = Math.max(0, this.arfagem);
        const forcaResistente = V.peso_total_N * Math.sin(subida)
            + PARAMETROS.ambiente.piso.crr_asfalto * V.peso_total_N * Math.cos(this.arfagem)
            + (this.modoEscada ? 0.12 * V.peso_total_N : 0);
        this.torquePorRoda = (forcaResistente * raioEfMedio) / PW.num_motores;

        const omegaSaida = Math.abs(this.velocidade) / Math.max(raioEfMedio, 0.05);
        const tensao = this.bateria.tensao(this.correnteTotal);
        const disponivel = this.motor.ponto(omegaSaida, tensao).torque;
        this.margemTorque = disponivel / Math.max(this.torquePorRoda, 1e-3);

        let vAlvo = comando.velocidadeAlvo;
        if (this.margemTorque < 1.0) vAlvo *= Math.max(0.1, this.margemTorque);
        if (this.emProtecaoTermica) vAlvo = 0;
        this.velocidade += (vAlvo - this.velocidade) * Math.min(1, dt * 4.0);

        const correnteMotor = Math.min(this.motor.limite,
                                       this.motor.correnteParaTorque(this.torquePorRoda));
        this.correnteTotal = correnteMotor * PW.num_motores;
        this.bateria.consumir(tensao * this.correnteTotal + EN.consumo_eletronica_w, dt);
        this.termica.passo(correnteMotor, dt);
        if (this.termica.emProtecao) this.emProtecaoTermica = true;
        else if (this.termica.temperatura < this.termica.maxima - 25) this.emProtecaoTermica = false;

        // --- 3. deslocamento no plano ------------------------------------------
        if (comando.modo === 'spin') {
            this.rumo += comando.omega * dt;
        } else {
            const rumoEfetivo = comando.modo === 'crab' ? this.rumo + cmd.angulos.FL : this.rumo;
            if (comando.modo !== 'crab') {
                const raioCurva = Math.abs(comando.omega) > 1e-6
                    ? this.velocidade / comando.omega : Infinity;
                if (isFinite(raioCurva)) this.rumo += (this.velocidade / raioCurva) * dt;
            }
            const dx = -Math.sin(rumoEfetivo) * this.velocidade * dt;
            const dz = -Math.cos(rumoEfetivo) * this.velocidade * dt;
            if (!terreno.colideComParede(this.x + dx, this.z + dz, V.bitola_W / 2)) {
                this.x += dx; this.z += dz;
                this.distanciaPercorrida += Math.hypot(dx, dz);
            } else {
                this.velocidade *= 0.15;
            }
        }

        // --- 4. contato e suspensão das quatro rodas -----------------------------
        const dir = { x: -Math.sin(this.rumo), z: -Math.cos(this.rumo) };
        const cos = Math.cos(this.rumo), sin = Math.sin(this.rumo);
        const k = this.kSuspensao, c = this.cSuspensao;
        // Comprimento livre da mola: no repouso o ponto de fixação está na cota do
        // eixo (vao = 0) e a mola precisa entregar exatamente M·g/4.
        const livre = this.afundamentoEstatico;

        const raioNominal = this.raioMax;

        let somaF = 0, momentoArfagem = 0, momentoRolagem = 0;
        for (const id of IDS_RODAS) {
            const roda = this.rodas[id];
            const p = POSICOES_RODAS[id];
            const wx = this.x + p.x * cos + p.z * sin;
            const wz = this.z - p.x * sin + p.z * cos;
            roda.atualizarAlvo(terreno, wx, wz, dir, this.velocidade, dt);

            // cota do ponto de fixação da suspensão neste canto
            const alavancaArfagem = -p.z;    // frente positiva
            const alavancaRolagem = p.x;     // direita positiva
            const yFixacao = this.y - OFFSET_CG
                + alavancaArfagem * Math.sin(this.arfagem)
                + alavancaRolagem * Math.sin(this.rolagem);
            const vFixacao = this.velY
                + alavancaArfagem * this.velArfagem * Math.cos(this.arfagem)
                + alavancaRolagem * this.velRolagem * Math.cos(this.rolagem);

            const vao = yFixacao - roda.altura;
            let forca = k * (livre - vao) + c * (roda.velocidade - vFixacao);
            const compressao = livre - vao;
            if (Math.abs(compressao) > SUS.curso_maximo) {
                forca += 2.0e4 * (Math.abs(compressao) - SUS.curso_maximo) * Math.sign(compressao);
            }
            forca = Math.max(-150, Math.min(600, forca));

            roda.integrar(forca, dt);
            roda.girar(this.velocidade, dt);

            somaF += forca;
            momentoArfagem += forca * alavancaArfagem;
            momentoRolagem += forca * alavancaRolagem;
        }

        // --- 5. corpo suspenso ---------------------------------------------------
        const M = PARAMETROS.massas.massa_total;
        const iArfagem = (M * V.entre_eixos_L * V.entre_eixos_L) / 12 * 1.6;
        const iRolagem = (M * V.bitola_W * V.bitola_W) / 12 * 1.6;

        const acelY = somaF / M - G;
        this.velY += acelY * dt;
        this.y += this.velY * dt;

        this.velArfagem += (momentoArfagem / iArfagem) * dt;
        this.arfagem += this.velArfagem * dt;
        this.velRolagem += (momentoRolagem / iRolagem) * dt;
        this.rolagem += this.velRolagem * dt;
        this.arfagem = Math.max(-1.4, Math.min(1.4, this.arfagem));
        this.rolagem = Math.max(-1.0, Math.min(1.0, this.rolagem));

        // --- 6. pêndulo da caixa e aceleração na carga ----------------------------
        const braco = V.braco_pendular;
        const acelPendulo = -(G / braco) * Math.sin(this.pendulo - this.arfagem)
                            - V.amortecimento_pendular * (this.velPendulo - this.velArfagem);
        this.velPendulo += acelPendulo * dt;
        this.pendulo += this.velPendulo * dt;

        this.aceleracaoCarga.vertical = (acelY + braco * acelPendulo * Math.sin(this.pendulo)) / G;
        this.aceleracaoCarga.longitudinal = (braco * acelPendulo * Math.cos(this.pendulo)) / G;
        if (this.tempo > 1.0) {
            this.picoCargaG = Math.max(this.picoCargaG, Math.abs(this.aceleracaoCarga.vertical));
        }

        // --- 7. cargas normais e atrito -------------------------------------------
        this.forcasNormais = this.cargasNormais();
        for (const id of IDS_RODAS) this.rodas[id].forcaNormal = this.forcasNormais[id];
        const muExigido = Math.tan(Math.abs(this.arfagem)) + PARAMETROS.ambiente.piso.crr_asfalto;
        this.escorregando = muExigido > PARAMETROS.ambiente.piso.mu_borracha_concreto;
    }

    cargasNormais() {
        const w = V.peso_total_N * Math.cos(this.arfagem) * Math.cos(this.rolagem);
        const h = V.altura_cg_total, L = V.entre_eixos_L, B = V.bitola_W;
        const transLong = (V.peso_total_N * Math.sin(this.arfagem) * h) / L;
        const transLat = (V.peso_total_N * Math.sin(this.rolagem) * h) / B;
        const fDianteiro = w / 2 - transLong;
        const fTraseiro = w / 2 + transLong;
        return {
            FL: Math.max(0, fDianteiro / 2 - transLat / 2),
            FR: Math.max(0, fDianteiro / 2 + transLat / 2),
            RL: Math.max(0, fTraseiro / 2 - transLat / 2),
            RR: Math.max(0, fTraseiro / 2 + transLat / 2),
        };
    }

    get limiarArfagem() {
        return this.modoEscada
            ? PARAMETROS.controle.pitch_critico_escada_deg
            : PARAMETROS.controle.pitch_critico_plano_deg;
    }

    /** Verdadeiro se a roda montada satisfaz a condição de marcha síncrona. */
    get marchaSincrona() {
        return alcanceNarizANariz(this.raioMax) >= PARAMETROS.ambiente.escada.passo_D;
    }

    get alertaTombamento() {
        return Math.abs(this.arfagem) * 57.2958 > this.limiarArfagem
            || Math.abs(this.rolagem) * 57.2958 > PARAMETROS.controle.roll_critico_deg;
    }

    /** Linha de telemetria para exportação em CSV. */
    telemetria() {
        return {
            t: this.tempo, x: this.x, z: this.z, y: this.y,
            velocidade: this.velocidade,
            arfagem_deg: this.arfagem * 57.2958,
            rolagem_deg: this.rolagem * 57.2958,
            carga_vert_g: this.aceleracaoCarga.vertical,
            carga_long_g: this.aceleracaoCarga.longitudinal,
            corrente_A: this.correnteTotal,
            tensao_V: this.bateria.tensao(this.correnteTotal),
            soc: this.bateria.soc,
            temp_motor_C: this.termica.temperatura,
            margem_torque: this.margemTorque,
            fz_FL: this.forcasNormais.FL, fz_FR: this.forcasNormais.FR,
            fz_RL: this.forcasNormais.RL, fz_RR: this.forcasNormais.RR,
            csts_FL_deg: this.rodas.FL.deflexaoCsts * 57.2958,
            energia_csts_J: IDS_RODAS.reduce((a, id) => a + this.rodas[id].energiaCsts, 0),
        };
    }
}
