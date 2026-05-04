# Google Scholar Alerts review for adaptive control of heterogeneous distributed computing systems

Дата подготовки: 2026-05-03.

Источник: Gmail, непрочитанные письма от `scholaralerts-noreply@google.com`.

Охват:

- найдено 284 непрочитанных письма Google Scholar Alerts за период примерно 2024-10-24 - 2026-05-02;
- тематический фильтр по ядру проекта (`task offloading`, `resource allocation`, `edge computing`, `MEC`, `federated learning`, `reinforcement learning`, `distributed computing`, `heterogeneous`) дал 149 писем/срабатываний;
- после ручной дедупликации видимых заголовков из Gmail search summaries получилось около 136 уникальных работ в тематическом ядре;
- этот документ основан на текстах alert/snippet и частично на телах первых писем; это не замена обзору по полным PDF.

## Executive summary

Основной массив Google Scholar Alerts складывается вокруг одной достаточно цельной линии: адаптивное управление вычислениями в edge/fog/cloud/MEC средах, где задачи нужно распределять между неоднородными узлами, транспортными средствами, UAV, LEO/SAGIN-сегментами, локальными edge-серверами и облаком. Почти все релевантные работы формулируют проблему как совместную оптимизацию задержки, энергопотребления, стоимости, надежности, QoS/QoE, безопасности и иногда приватности. Это хорошо ложится на тематику "adaptive control of heterogeneous distributed computing systems": здесь важны онлайн-решения, динамическое состояние сети, неполная информация, зависимые задачи, мобильность пользователей и изменение доступных ресурсов.

Самый сильный кластер - task offloading and resource allocation in MEC. В нем повторяются три класса постановок. Первый: классическая совместная оптимизация offloading/resource allocation/caching, где управляемыми переменными являются выбор места исполнения задачи, полоса/канал, вычислительные ресурсы, кэширование сервиса или контента и иногда траектория UAV. Второй: multi-objective formulations, где цель уже не одна метрика, а компромисс delay-energy-cost-reliability. Третий: зависимые задачи и workflow, где задача представлена графом или DAG, поэтому простая независимая маршрутизация задач уже недостаточна. Для нашего проекта это важный сигнал: модель нагрузки должна поддерживать не только независимые jobs, но и зависимости, приоритеты, deadline/QoS-классы и динамическое перераспределение.

Второй крупный кластер - reinforcement learning и deep reinforcement learning для управления offloading. Здесь заметен сдвиг от эвристик и статической оптимизации к RL/DRL/MARL: DQN, PPO, DDPG/TD3, multi-agent DRL, graph reinforcement learning, meta-DRL и stochastic games. Работы используют RL там, где состояние среды меняется быстрее, чем можно надежно решать статическую задачу оптимизации: мобильные узлы, UAV, vehicular edge computing, NOMA/MIMO, LEO, энергосбор, неполная информация о вычислительной мощности, меняющаяся пропускная способность и разные профили задач. Для проекта это подтверждает выбранную линию с адаптивным агентом/политикой: эвристики нужны как baseline, но центральная научная новизна может строиться вокруг обучаемого/самонастраиваемого диспетчера.

Третий кластер - federated learning, federated reinforcement learning and privacy-preserving edge intelligence. Он связан не только с обучением моделей без централизации данных, но и с распределенным принятием решений для offloading. В работах встречаются knowledge distillation, personalized FL, verifiable FL, blockchain-backed FL, group chaining, cold-start aggregation, anomaly detection in IoT edge, privacy-preserving task offloading и latency-critical federated decision-making. Для локальной RAG-системы это важная группа: она даст материал для раздела о приватности, робастности и масштабируемости управления, особенно если в проекте нужен аргумент, почему централизованный контроллер не всегда реалистичен.

Четвертый кластер - UAV/SAGIN/LEO/vehicular edge. Он наиболее близок к "heterogeneous distributed systems" по физической неоднородности среды. Здесь задачи распределяются между движущимися устройствами, UAV, ground edge, satellite/LEO edge, vehicles, roadside units и cloud. Типичные переменные: траектория UAV, beamforming, channel allocation, service caching, deployment, energy harvesting, data transmission schedule, task deadline, user mobility. Эти работы полезны как источник сценариев для симулятора: node mobility, intermittent connectivity, dynamic capacity, mixed terrestrial/non-terrestrial infrastructure.

Пятый кластер - metaheuristics/game theory/auction/contract/pricing. В alert-ах есть grey numbers, Hungarian algorithm, firefly algorithm, whale optimization, quantum-inspired PSO, snake optimizer, Pufferfish/Osprey hybrid optimization, contract theory, matching theory, auctions and pricing mechanisms. Этот пласт полезен как набор baseline-алгоритмов и как материал для сравнения с RL-подходами. Для публикационной части проекта можно разделить методы на exact/convex optimization, metaheuristics, game-theoretic mechanisms и learning-based controllers.

Есть и побочные ветки: YOLO/UAV small object detection, autonomous driving perception, 3D reconstruction/neural rendering, energy storage control, hybrid battery/supercapacitor systems. Они не являются центральными для RAG по распределенным вычислениям, но часть из них может быть полезна как прикладные источники workloads: computer vision inference on edge, autonomous driving tasks, UAV sensing pipelines, energy-aware scheduling. Такие статьи лучше пометить как secondary corpus, а не смешивать с core corpus.

## Core bibliography candidates

Ниже список видимых заголовков из релевантных Google Scholar Alerts. Дубликаты одинаковых заголовков сведены в одну строку. Для скачивания PDF/HTML на следующем шаге нужно пройти по телам писем и извлечь прямые Scholar redirect URLs или искать статьи по названию через arXiv/Crossref/Unpaywall/publisher pages.

### Task offloading, resource allocation and scheduling

1. Personalized Federated Learning for Intelligent Slice-Based Task Offloading and Slice Resource Allocation in Sliced B5G MEC-Enabled Network
2. Resource optimization for minimizing latency and cost in UAV-assisted mobile edge computing (MEC) networks
3. Optimizing Multi-UAV-Enabled MEC Networks for Deep Learning Tasks: A Joint Offloading and Deployment Approach
4. Category Attribute-Oriented Heterogeneous Resource Allocation and Task Offloading for SAGIN Edge Computing
5. Mobility-aware task offloading in UAV-MEC-assisted IoV: A two-stage approach
6. Minimizing energy consumption of collaborative deployment and task offloading in two-tier UAV edge computing networks
7. Task Offloading and Resource Scheduling in Mobile Edge-Cloud Computing Based on Edge Competition and Task Prediction
8. Multi-Objective Dependent Task Scheduling, Resource Allocation, and Service Caching in Aerial-Ground Integrated MEC
9. Joint Optimization of Task Offloading Content Caching and Resource Allocation in Vehicular Edge Computing
10. Energy-saving and security-enhanced task offloading strategies in D2D-integrated MEC networks
11. Joint Task Offloading and Channel Allocation in Spatial-Temporal Dynamic for MEC Networks
12. Optimizing Resource Allocation and Task Offloading in Multi-UAV MEC Networks
13. Fuzzy inference rule based task offloading model (FI-RBTOM) for edge computing
14. Dynamic Service Caching Aided Computation Offloading Optimization Algorithm for Mobile Edge Networks
15. Computation Offloading in Mobile Edge Computing-enabled Blockchain Based on Contract and Matching Theory
16. An Incentive Framework for Task Offloading in Edge Computing Marketplaces under Price Competition
17. Parking Vehicle-Assisted Task Offloading in Edge Computing: a dynamic multi-objective evolutionary algorithm with multi-strategy fusion response
18. Intelligent Offloading Balance for Vehicular Edge Computing and Networks
19. Dynamic OBL-driven Whale Optimization Algorithm for independent tasks offloading in fog computing
20. Computation Offloading and Resource Allocation in Mixed Cloud/Vehicular-fog Computing Systems
21. Joint Task Offloading and Resource Scheduling in Low Earth Orbit Satellite Edge Computing Networks
22. A graph reinforcement LearningPowered Online-Computational task offloading and latency minimization framework for wireless mobile edge computing networks
23. Quality of Experience and Reliability-Aware Task Offloading and Scheduling for Multi-User Mobile-Edge Computing Systems
24. A Dynamic Optimization Framework for Computation Rate Maximization in UAV-Assisted Mobile Edge Computing
25. Task Offloading and Resource Allocation in Vehicular Cooperative Perception With Integrated Sensing, Communication, and Computation
26. MOSO: multi-objective snake optimizer with density estimation and grid indexing mechanism for edge computing task offloading and scheduling optimization
27. Joint Task Offloading and Resource Allocation for LEO Satellite-Based Mobile Edge Computing Systems With Heterogeneous Task Demands
28. Vehicle-Assisted Service Caching for Task Offloading in Vehicular Edge Computing
29. Neural Combinatorial Optimization for Multiobjective Task Offloading in Mobile Edge Computing
30. Load-balanced multi-user mobility-aware task offloading in multi-access edge computing
31. Task Offloading and Multi-cache Placement Based on DRL in UAV-assisted MEC Networks
32. Task Offloading in Edge Computing Considering the Dynamics of Tasks and Networks Based on Grey Numbers
33. P2PPO: parallel residual network and prioritized experience replay enhanced PPO for task offloading and resource allocation in SatEC
34. Two-Timescale Hierarchical Contract for Joint Computation Offloading and Energy Management in Edge Computing System
35. Truthful Online Combinatorial Auction-based Mechanisms for Task Offloading in Mobile Edge Computing
36. UAV-Assisted MEC Architecture for Collaborative Task Offloading in Urban IoT Environment
37. A deep learning-based strategy for energy-efficient parallel computation offloading in mobile edge networks
38. Energy-efficient task offloading and efficient resource allocation for edge computing: a quantum inspired particle swarm optimization approach
39. Robust Task Offloading and Resource Allocation Under Imperfect Computing Capacity Information in Edge Intelligence Systems
40. Privacy-preserving and truthful auction-based resource allocation mechanisms for task offloading in mobile edge computing
41. Cooperative Service Caching and Task Offloading in Mobile Edge Computing: A Novel Hierarchical Reinforcement Learning Approach
42. Modeling and analysis of LoRa-enabled task offloading in edge computing for enhanced battery life in wearable devices
43. Incentivizing task offloading in IoT: A distributed auctions-based DRL approach
44. Task offloading and multi-cache placement in multi-access mobile edge computing
45. Joint Task Offloading and Resource Allocation in Mobile Edge Computing-Enabled Medical Vehicular Networks
46. Multi-task Oriented Efficient Computational Offloading Orchestrator for IoT Applications in Mobile Edge Computing
47. Robust Task Offloading and Trajectory Optimization for UAV-Mounted Mobile Edge Computing
48. Partial Task Offloading for UAV-assisted Mobile Edge Computing with Energy Harvesting
49. Reliability-Optimal UAV-Assisted Mobile Edge Computing: Joint Resource Allocation, Data Transmission Scheduling and Motion Control
50. Towards Optimal Train Control: An Edge Computing Approach With Adaptive Computation Offloading
51. Task offloading and resource allocation in cellular heterogeneous networks for NOMA-based mobile edge computing
52. Task Offloading and Resource Pricing Based on Game Theory in UAV-Assisted Edge Computing
53. QoS-Aware Augmented Reality Task Offloading and Resource Allocation in Cloud-Edge Collaboration Environment
54. Offloading Revenue Maximization in Multi-UAV-Assisted Mobile Edge Computing for Video Stream
55. Joint Trajectory Planning and Task Offloading for MIMO UAV-aided Mobile Edge Computing
56. Integrating of IOTA-based blockchain with edge computing for task offloading powering the metaverse
57. Dependency-Aware Joint Task Offloading and Resource Allocation in Heterogeneous Mobile Edge Computing
58. Enhancing 5G Vehicular Edge Computing Efficiency with the Hungarian Algorithm for Optimal Task Offloading
59. Adaptive Task Offloading for Mobile Edge Computing With Forecast Information
60. Fault tolerant & priority basis task offloading and scheduling model for IoT logistics
61. Enhanced Task Scheduling and Resource Allocation in Edge-Cloud continuum Using Modified Flower Pollination Algorithm
62. Multi-Objectives Firefly Algorithm for Task Offloading in the Edge-Fog-Cloud Computing
63. Offloading computational tasks for MIMO-NOMA in mobile edge computing utilizing a hybrid Pufferfish and Osprey optimization algorithm
64. SITOff: Enabling Size-Insensitive Task Offloading in D2D-Assisted Mobile Edge Computing
65. DELIGHT: a willingness-aware collaborative edge service offloading utilizing deep reinforcement learning
66. UAV-mounted IRS assisted wireless powered mobile edge computing systems: Joint beamforming design, resource allocation and position optimization

### Reinforcement learning, adaptive control and multi-agent methods

1. Multi-agent Deep Reinforcement Learning-Based Hierarchical Scheduling in Heterogeneous UAVs Enabled Vehicular Networks
2. A Knowledge Distillation-empowered Adaptive Federated Reinforcement Learning Framework for Multi-Domain IoT Applications Scheduling
3. EADRL: Efficiency-Aware Adaptive Deep Reinforcement Learning for Dynamic Task Scheduling in Edge-Cloud Environments
4. Tensor-Based Efficient Federated Reinforcement Learning for Cyber-Physical-Social Intelligence
5. Trustworthy AI for 6G-IoV: A Privacy-Preserved Distributed Multiagent Federated DRL for Dynamic Electric Vehicle Charging and Task Offloading
6. Federated Reinforcement Learning-Based Dynamic Resource Allocation and Task Scheduling in Edge for IoT Applications
7. Reinforcement Learning-Driven Task Offloading and Resource Allocation in Wireless IoT Networks
8. A Blockchain-enabled Cold Start Aggregation Scheme for Federated Reinforcement Learning-based Task Offloading in Zero Trust LEO Satellite Networks
9. Efficient and Sustainable Task Offloading in UAV-Assisted MEC Systems via Meta Deep Reinforcement Learning
10. Multi-Agent Reinforcement Learning for Graph Discovery in D2D-Enabled Federated Learning
11. A Multi-Agent Federated DRL Model for Vehicular Task Offloading in WPT-Aided eROAD Environment
12. Federated Twin Delayed Deep Deterministic Policy Gradient for Delay and Energy Consumption Optimization in Urban Air Mobility with UAV-Assisted MEC
13. A Learning-Based Stochastic Game for Energy Efficient Optimization of UAV Trajectory and Task Offloading in Space/Aerial Edge Computing
14. Federated deep reinforcement learning-based cost-efficient proactive video caching in energy-constrained mobile edge networks
15. Heterogeneous multi-agent deep reinforcement learning based low carbon emission task offloading in mobile edge computing
16. Multi-Agent Reinforcement Learning for Task Offloading in Crowd-Edge Computing
17. DRL-based latency-energy offloading optimization strategy in wireless VR networks with edge computing
18. Meta learning-based deep reinforcement learning algorithm for task offloading in dynamic vehicular network
19. Deep Reinforcement Learning-based Resource Management for Task Offloading in Integrated Terrestrial and Non-Terrestrial Networks
20. A Deep Reinforcement Learning Approach for Dependent Task Offloading in Multi-Access Edge Computing
21. Task Offloading with LLM-Enhanced Multi-Agent Reinforcement Learning in UAV-Assisted Edge Computing
22. Research on Task Offloading and Delay Optimization of Unmanned Aerial Vehicle-Assisted Medical Edge Computing Based on Deep Reinforcement Learning
23. Mobility-Aware Partial Task Offloading and Resource Allocation Based on Deep Reinforcement Learning for Mobile Edge Computing
24. Deep Reinforcement Learning Based Task Offloading and Resource Allocation in Mobile Edge Computing Network With Heterogeneous Tasks
25. Adaptive Prioritization and Task Offloading in Vehicular Edge Computing Through Deep Reinforcement Learning
26. Graph Convolutional Reinforcement Learning-Guided Joint Trajectory Optimization and Task Offloading for Aerial Edge Computing
27. Multi-objective Deep Reinforcement Learning for Function Offloading in Serverless Edge Computing
28. DRL-Based Trajectory Optimization and Task Offloading in Hierarchical Aerial MEC
29. Asynchronous Fractional Multi-Agent Deep Reinforcement Learning for Age-Minimal Mobile Edge Computing
30. A deep Q-learning model for sequential task offloading in edge AI systems

### Federated learning, privacy, trust and distributed intelligence

1. Mobility-aware decentralized federated learning with joint optimization of local iteration and leader selection for vehicular networks
2. Federated Learning with Sailfish-Optimized Ensemble Models for Anomaly Detection in IoT Edge Computing Environment
3. Data-Driven Incentive Mechanisms for Federated Learning in Vehicular Networks
4. A scalable federated learning-based approach for accurate traffic prediction in edge computing-enable metro optical network
5. Verifiable Federated Learning with Group Chaining in Edge Computing
6. Federated Learning for Trust Enhancement in UAV-Enabled IoT Networks: A Unified Approach
7. Intelligent deep federated learning model for enhancing security in internet of things enabled edge computing environment
8. Efficient Vehicle Selection and Resource Allocation for Knowledge Distillation-Based Federated Learning in UAV-Assisted VEC
9. FedShufde: A privacy preserving framework of federated learning for edge-based smart UAV delivery system
10. FLSN-MVO: Edge Computing and Privacy Protection Based on Federated Learning Siamese Network With Multi-Verse Optimization Algorithm for Industry 5.0
11. PopFL: A scalable Federated Learning model in serverless edge computing integrating with dynamic pop-up network
12. New Continual Federated Learning System for Intrusion Detection in SDN-Based Edge Computing
13. Tensor Dynamic Fusion Based Modality-Imbalanced Multimodal Federated Learning in Mobile Edge Computing for Consumer Applications
14. Privacy-Preserving Knowledge Distillation in Latency-Critical Federated Task Offloading for Consumer IoT Networks
15. LiteChain: A Lightweight Blockchain for Verifiable and Scalable Federated Learning in Massive Edge Networks
16. Federated learning for edge artificial intelligence: Enhancing security, robustness, privacy, personalization, and blockchain integration in IoT

### Adjacent workloads and secondary corpus

1. An Energy-Efficient Edge Coprocessor for Neural Rendering with Explicit Data Reuse Strategies
2. Pose Optimization for Autonomous Driving Datasets using Neural Rendering Models
3. Data-Driven DLT3 Federated Deep Reinforcement Learning for Secure and Efficient Autonomous Driving
4. Towards Human-Centric Autonomous Driving: A Fast-Slow Architecture Integrating Large Language Model Guidance with Reinforcement Learning
5. Enhancing Dependability of Fog Computing Using Learning-based Task Scheduling
6. Enhancing E-business in industry 4.0: Integrating fog/edge computing with Data LakeHouse for IIoT
7. AI-Powered Edge Computing in Cloud Ecosystems: Enhancing Latency Reduction and Real-Time Decision-Making in Distributed Networks
8. Deep Reinforcement Learning-Based Mobile Battery Energy Storage System Control With Partial Observability and Data Imputation
9. A hierarchical real-time energy management and control strategy for fully-active battery/supercapacitor hybrid energy storage system
10. MV-YOLO: An Efficient Small Object Detection Framework Based on Mamba
11. SD-YOLO: A Robust and Efficient Object Detector for Aerial Image Detection
12. LRDS-YOLO enhances small object detection in UAV aerial images with a lightweight and efficient design
13. Edge-Optimized Lightweight YOLO for Real-Time SAR Object Detection
14. BSE-YOLO: An Enhanced Lightweight Multi-Scale Underwater Object Detection Model
15. Learning Partonomic 3D Reconstruction from Image Collections
16. DAU-YOLO: A Lightweight and Effective Method for Small Object Detection in UAV Images
17. YOLO-Air: An Efficient Deep Learning Network for Small Object Detection in Drone-Based Imagery
18. YOLO-DAFS: A Composite-Enhanced Underwater Object Detection Algorithm
19. RLRD-YOLO: An Improved YOLOv8 Algorithm for Small Object Detection from an Unmanned Aerial Vehicle (UAV) Perspective
20. Effectiveness of Teachable Machine, mobile net, and YOLO for object detection: A comparative study on practical applications

## What this means for the project

The literature suggests that the strongest framing is not simply "task scheduling", but "adaptive, multi-objective control of task offloading and resource allocation in heterogeneous edge-cloud systems under uncertainty". This wording captures the common problem across the alerts and connects directly to the codebase's simulation, agent, QoS, prediction and optimization modules.

Key dimensions to reflect in experiments:

- Heterogeneity: nodes should differ by compute capacity, queue delay, energy profile, reliability and communication bandwidth.
- Dynamics: workloads and links should change over time; static one-shot assignment is too weak as a main case.
- Uncertainty: several papers explicitly handle imperfect capacity information, partial observability, forecast information or mobility.
- Multi-objective control: latency-only optimization is insufficient; relevant papers balance latency, energy, cost, reliability, privacy and QoS/QoE.
- Topology: core scenarios should include edge-cloud, vehicular edge, UAV-assisted MEC and possibly LEO/SAGIN-like high-latency nodes.
- Learning-based policies: DRL/MARL/federated RL is the dominant modern thread, but metaheuristics and game-theoretic mechanisms are useful baselines.

## Suggested first RAG corpus

For the first local RAG build, prioritize papers that are closest to the project and likely to provide reusable terminology, models and baselines:

1. Dependency-Aware Joint Task Offloading and Resource Allocation in Heterogeneous Mobile Edge Computing
2. Deep Reinforcement Learning Based Task Offloading and Resource Allocation in Mobile Edge Computing Network With Heterogeneous Tasks
3. Adaptive Task Offloading for Mobile Edge Computing With Forecast Information
4. Task Offloading and Resource Scheduling in Mobile Edge-Cloud Computing Based on Edge Competition and Task Prediction
5. EADRL: Efficiency-Aware Adaptive Deep Reinforcement Learning for Dynamic Task Scheduling in Edge-Cloud Environments
6. Quality of Experience and Reliability-Aware Task Offloading and Scheduling for Multi-User Mobile-Edge Computing Systems
7. Robust Task Offloading and Resource Allocation Under Imperfect Computing Capacity Information in Edge Intelligence Systems
8. Multi-Objective Dependent Task Scheduling, Resource Allocation, and Service Caching in Aerial-Ground Integrated MEC
9. Joint Task Offloading and Resource Allocation for LEO Satellite-Based Mobile Edge Computing Systems With Heterogeneous Task Demands
10. Joint Task Offloading and Resource Scheduling in Low Earth Orbit Satellite Edge Computing Networks
11. Federated Reinforcement Learning-Based Dynamic Resource Allocation and Task Scheduling in Edge for IoT Applications
12. A Knowledge Distillation-empowered Adaptive Federated Reinforcement Learning Framework for Multi-Domain IoT Applications Scheduling
13. Heterogeneous multi-agent deep reinforcement learning based low carbon emission task offloading in mobile edge computing
14. Multi-Agent Reinforcement Learning for Task Offloading in Crowd-Edge Computing
15. Graph Convolutional Reinforcement Learning-Guided Joint Trajectory Optimization and Task Offloading for Aerial Edge Computing
16. Mobility-aware decentralized federated learning with joint optimization of local iteration and leader selection for vehicular networks
17. Privacy-Preserving Knowledge Distillation in Latency-Critical Federated Task Offloading for Consumer IoT Networks
18. LiteChain: A Lightweight Blockchain for Verifiable and Scalable Federated Learning in Massive Edge Networks
19. Enhanced Task Scheduling and Resource Allocation in Edge-Cloud continuum Using Modified Flower Pollination Algorithm
20. Multi-Objectives Firefly Algorithm for Task Offloading in the Edge-Fog-Cloud Computing

## Next extraction steps for a local RAG system

1. Read the bodies of the 149 relevant Gmail messages and extract article-level records:
   `title`, `authors`, `venue`, `year`, `abstract/snippet`, `alert_date`, `access_hint`, `scholar_redirect_url`, `direct_url_if_visible`.
2. Resolve direct URLs:
   arXiv links by arXiv id; DOI/publisher links through Crossref; open PDFs through Unpaywall or direct publisher PDF links where legally available.
3. Store metadata in `data/literature/google_scholar_alerts.csv` or JSONL.
4. Download only open-access/full-text-available papers into `data/papers/`.
5. Extract text with `pypdf`/GROBID-style fallback, keep page metadata and source URL.
6. Chunk by section/page, embed chunks, and build a local FAISS/Chroma index.
7. Add a small query layer with citations: return title, page/chunk, URL, and confidence.

Important: Google Scholar redirect links are useful for discovery but are not stable long-term metadata. The durable RAG metadata should prefer DOI, arXiv id, publisher URL, PDF URL and local file hash.
