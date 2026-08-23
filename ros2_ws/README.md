# Workspace ROS 2 — Rover Frugal 4WD/4WS

> **Alvo:** ROS 2 **Jazzy Jalisco** (LTS) com **Gazebo Harmonic** (`gz-sim` 8).
> Compatível com Kilted/Gazebo Ionic trocando apenas as dependências binárias.

## Compilar

```bash
cd ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

## Rodar

```bash
# Percurso completo de homologação (roda com aro elástico)
ros2 launch rover_frugal_bringup missao.launch.py

# Ensaio de subida de escada, sem interface, com telemetria em CSV
ros2 launch rover_frugal_bringup ensaio_escada.launch.py arquivo:=/tmp/ens06.csv

# Restrição operacional de A-10: a mesma escada com piso molhado (μ = 0,55)
ros2 launch rover_frugal_gazebo simulacao.launch.py mundo:=escada_molhada.sdf aro_elastico:=false

# Só a geometria, no RViz
ros2 launch rover_frugal_description visualizar.launch.py
```

## Pacotes

| Pacote | Conteúdo |
| :--- | :--- |
| `rover_frugal_description` | URDF/xacro, malhas STL, RViz. **Sem números**: lê `config/parametros.yaml`, gerado do arquivo mestre |
| `rover_frugal_control` | cinemática 4WS, molas passivas (suspensão e C-STS), supervisor de segurança |
| `rover_frugal_gazebo` | mundos SDF gerados dos parâmetros, ponte `ros_gz`, launch da simulação |
| `rover_frugal_bringup` | missão completa, ensaios instrumentados, registrador de telemetria |

## Regenerar os artefatos

Nada aqui é editado à mão quando a geometria muda. Depois de alterar
`00_Especificacao_Mestre/parametros_mestres.yaml`:

```bash
python3 ferramentas/gerar_malhas.py          # malhas STL
python3 ferramentas/gerar_ros_config.py      # parametros.yaml + controladores.yaml
python3 ferramentas/gerar_mundo_gazebo.py    # mundos SDF
python3 -m pytest testes/test_ros_urdf.py -q # verificação
```

Ver [`03_Simulacao_e_Prototipacao_Digital/05_ROS2_e_Gazebo.md`](../03_Simulacao_e_Prototipacao_Digital/05_ROS2_e_Gazebo.md)
para as decisões de modelagem e as limitações conhecidas.
