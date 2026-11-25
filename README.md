<div align="center">

  <img src="Docs/logo.png" alt="NeuralEyeTracker Logo" width="520" />

  <p><sub>Adaptive Neurocognitive Architectures — Evolutionary Modeling and Intelligent Decision Support in Defense of the Human Subject</sub></p>

  <p>
    <img src="https://img.shields.io/badge/Core-Python_3-3776AB?logo=python&logoColor=white" alt="Python 3" />
    <img src="https://img.shields.io/badge/Computer_Vision-OpenCV-5C3EE8?logo=opencv&logoColor=white" alt="OpenCV" />
    <img src="https://img.shields.io/badge/Desktop_GUI-PyQt5-41CD52?logo=qt&logoColor=white" alt="PyQt5" />
    <img src="https://img.shields.io/badge/Web_Interface-React_%2B_TypeScript-61DAFB?logo=react&logoColor=black" alt="React + TypeScript" />
    <img src="https://img.shields.io/badge/Architecture-Neuro--Adaptive_Closed--Loop-ff8c00" alt="Neuro-Adaptive" />
    <img src="https://img.shields.io/badge/Research-Tokaj--Hegyalja_University-2ea44f" alt="Research" />
  </p>

  <p><strong>Real-Time Oculometric &amp; Pupillometric Cognitive State Monitoring System Designed Around Human Sovereignty and Meaningful Human Control</strong></p>

</div>

---

## Executive Overview

**NeuralEyeTracker** is an experimental, analytical, and decision-support software platform developed alongside the BSc thesis *"Adaptive Neurocognitive Architectures: Evolutionary Modeling and Intelligent Decision Support in Defense of the Human Subject"* (Tokaj-Hegyalja University, Computer Science BSc). The system addresses a critical vulnerability shared across high-stakes operational environments—ranging from tactical military command to clinical radiology, pathology, and intensive care: **silent cognitive failure**.

When human operators or clinical specialists experience acute mental fatigue, sleep deprivation, or working-memory saturation, their operational pace often remains outwardly unchanged while diagnostic or tactical accuracy deteriorates sharply. Because fatigue degrades metacognitive self-monitoring, subjective self-assessment cannot reliably detect cognitive overload in real time. **NeuralEyeTracker** bridges this gap by extracting high-resolution oculometric and pupillometric biomarkers from non-invasive video streams and translating them into actionable, human-centric protective interventions.

> *"A wealth of information creates a poverty of attention. An effective system must not maximize information—it must protect human attention."* — **Herbert A. Simon**

---

## Core Architectural Philosophy

The engineering design of **NeuralEyeTracker** rests on three foundational pillars:

1. **Biological Plausibility & Individual Baseline Calibration**
   Autonomic pupillary dynamics and oculomotor kinematics exhibit substantial inter-individual variance. Rather than enforcing rigid population norms that trigger false alarms or missed detections, the system establishes a personalized resting baseline at the start of each session and evaluates relative deviations ($z$-score normalization) alongside slow circadian drift compensation.
2. **Closed-Loop Bounded Agent Complementarity**
   Drawing on Cognitive Load Theory (CLT) and the ACT-R cognitive architecture, human working memory ($4 \pm 1$ chunks) and machine context/attention mechanisms both suffer non-linear degradation under overload. NeuralEyeTracker acts as a real-time feedback regulator that keeps the human operator within an optimal, productive cognitive load band without inducing automation bias or skill atrophy.
3. **Human-Subject Protection by Design**
   Ethical safeguards—cognitive sovereignty, mental privacy, interpretability, and Meaningful Human Control (MHC)—are operationalized directly into software mechanisms rather than treated as post-hoc policy statements.

---

## Four-Layer Conceptual & Functional Architecture

The platform is organized into four hierarchical, closed-loop processing layers:

| Layer | Functional Role | Key Mechanisms & Outputs |
|---|---|---|
| **1. Data Acquisition & Signal Processing** | Sensory front-end for non-invasive video-oculography (VOG) | Dynamic Eye-ROI segmentation, CLAHE contrast enhancement, adaptive/Otsu thresholding, sub-pixel ellipse fitting, blink artifact rejection, illumination baseline compensation |
| **2. Feature Extraction & State Estimation** | Transformation of cleaned kinematic and pupillary time series into neurocognitive states | 13-dimensional physical feature vector, personalized baseline normalization, Kalman & exponential smoothing, neural regression (`MLPRegressor`), composite cognitive indices |
| **3. Adaptive Decision & Intervention** | Context-aware evaluation of operator readiness and protective response | Flow vs. overload discrimination, calibrated deceleration, gaze-coverage quality assurance, gradual reversible task delegation |
| **4. Human Feedback & Override** | Transparency, metacognitive reinforcement, and sovereign human authority | Live cognitive dashboard, explainable alert triggers, single-action manual veto, subjective feedback loop |

---

## Computer Vision & Oculometric Pipeline

**NeuralEyeTracker** decouples deterministic, auditable computer vision processing from machine-learning inference so that every measurement remains physically interpretable and traceable.

### Multi-Stage Pupil Detection Pipeline

1. **Dynamic Region of Interest (`EyeSegmenter`):** Localizes the ocular bounding box per frame, falling back gracefully to prior tracked coordinates if transient occlusion occurs.
2. **Photometric Preprocessing:** Applies Contrast Limited Adaptive Histogram Equalization (CLAHE), bilateral filtering, and Gaussian smoothing to stabilize iris–pupil boundaries under uneven lighting.
3. **Hybrid Thresholding & Morphological Cleaning:** Combines adaptive, Otsu, and fixed intensity thresholding followed by morphological opening and closing to isolate candidate contours.
4. **Multi-Criteria Candidate Scoring:** Evaluates each contour across six normalized quality dimensions—darkness, circularity ($C = \frac{4\pi A}{P^2}$), aspect ratio, spatial proximity to the prior center, iris–pupil ring contrast ($\Delta I = \bar{I}_{\text{ring}} - \bar{I}_{\text{pupil}}$), and scale consistency—computing a weighted score $S = \sum_{i=1}^{6} w_i q_i$.
5. **Explicit Confidence & Blink Handling:** Failed detections or blinks (consecutive low-confidence frames) are explicitly flagged (`detected = False`, zero confidence) and excluded from statistical aggregation rather than masked by synthetic interpolation.

### 13-Dimensional Feature Representation & Gaze Estimation

Extracted ocular geometry is mapped into a scale- and anatomy-invariant feature vector:

$$\boldsymbol{\phi} = [d_x, d_y, x, y, a_n, b_n, \alpha_n, A_n, r, \delta, c, v_x, v_y]^\mathsf{T}$$

* **Relative Baseline Offsets ($d_x, d_y$):** Clipped, gain-scaled deviations from the user's robust median resting pupil center $(x_0, y_0)$.
* **Normalized Spatial & Ellipse Geometry ($x, y, a_n, b_n, \alpha_n, A_n, r$):** Frame-normalized gaze coordinates, major/minor ellipse axes, orientation angle, area, and aspect ratio.
* **Photometric & Dynamic Features ($\delta, c, v_x, v_y$):** Pupil–iris contrast, darkness metric, and inter-frame ocular velocity components.

A personalized multi-layer perceptron (`NeuralGazeModel`) standardized via `StandardScaler` maps $\boldsymbol{\phi}$ to calibrated azimuth and elevation angles, stabilized temporally through a linearly weighted sliding window. Prior to calibration completion (requiring $\ge 30$ valid target samples), a deterministic geometric fallback provides continuous preview tracking without polluting validated model metrics.

---

## Composite Neurocognitive Indices

The state-estimation layer synthesizes oculomotor kinematics (saccades, fixations, microsaccades, smooth pursuit) and pupillary dynamics (tonic baseline vs. phasic Task-Evoked Pupillary Response, TEPR) into four composite indices:

| Composite Index | Primary Oculometric Biomarkers | Monitored Neurocognitive State | Protective Function |
|---|---|---|---|
| **Cognitive Load Index** | Phasic pupillary dilation (TEPR), microsaccade rate, fixation duration prolongation | Working-memory load & processing effort | Prevents cognitive saturation and attentional tunneling |
| **Attention Score** | Scanpath spatial entropy, off-target fixation ratio, saccadic main-sequence dynamics | Sustained focus & visual scanning efficiency | Detects attentional drift and spatial neglect |
| **Fatigue Index** | Tonic pupil diameter constriction, pupillary hippus waves, blink rate & PERCLOS | Vigilance & central nervous system arousal | Early warning prior to microsleeps and silent errors |
| **Neurological Integrity Index** | Pupillary Light Reflex (PLR) latency, constriction velocity, anisocoria, saccadic gain | Brainstem & cortical oculomotor pathway integrity | Rapid screening for latent trauma (mTBI) or neurological deficit |

Crucially, interventions are governed by **multivariate state trajectories** rather than single thresholds: high cognitive load paired with high attention and low fatigue reflects productive *flow* (where intervention is suppressed), whereas rising load accompanied by climbing fatigue and collapsing attention triggers protective support.

---

## Experimental Protocol, Data Model & Reporting

The desktop application orchestrates structured psychophysiological experiments in a dedicated non-blocking worker thread (`TrackerThread`), preserving 60 FPS UI responsiveness in PyQt5 while stabilizing live coordinates with a Kalman filter and exponential smoothing.

* **Affective & Cognitive Stimulus Engine (`StimulusTask`):** Dynamically loads categorized visual stimulus sets (`neutral`, `positive`, `negative`, `threat`, `trauma`) and supports integrated Stroop interference tasks alongside Visual Analog Scale (VAS) subjective self-ratings.
* **Hierarchical Data Model:** Organizes sessions from **Project** metadata (validated subject identifiers and study objectives) through **ExperimentResult** summaries down to individual **Trial** records capturing baseline/min/max/mean pupil diameter, variance, fixation time, reaction time, blink flags, and detection confidence.
* **Statistical Aggregation & Multi-Format Export (`Analyzer` & `ReportGenerator`):** Filters non-finite or low-confidence samples, groups metrics by stimulus category, subject, or trial index, and exports publication-ready **HTML** reports, structured **JSON** session archives, and statistical **CSV** tables—always embedding explicit clinical decision-support disclaimers.

---

## Dual-Use Application Domains

### 1. Clinical Diagnostics & Fatigue-Aware Medical AI
* **Neurology & Psychiatry:** Objective digital biomarkers for early screening and longitudinal monitoring in mild Traumatic Brain Injury (mTBI), Alzheimer's and Parkinson's disease (antisaccade error rates, saccadic hypometria, PLR attenuation), schizophrenia spectrum disorders (smooth pursuit deficits, restricted scanpaths), PTSD (autonomic hyperarousal), major depressive disorder (affective attentional bias), and ASD/ADHD.
* **Clinician Protection & Gaze-Coverage QA:** Rather than naively lowering AI tumor-detection thresholds when a radiologist or pathologist fatigues (which exacerbates automation bias), NeuralEyeTracker compares the clinician's foveal gaze heatmap against high-risk anatomical regions—flagging under-explored zones before sign-off and triggering peer-review routing or rest breaks under sustained fatigue.

### 2. Tactical Operations & Human-Machine Teaming
* **Situational Awareness & Vigilance:** Detects attentional tunneling in multi-sensor C4ISR consoles and vigilance decrements during extended surveillance or drone operations.
* **Field Neurological Triage & Training:** Enables rapid 30-second PLR and saccadic screening for blast-induced mTBI, and quantifies the hidden "cognitive cost" of tactical simulations for adaptive stress-inoculation training.
* **Gradual, Reversible Delegation:** Implements a three-tier proactivity model (*Manual Assisted* $\rightarrow$ *Management by Consent* $\rightarrow$ *Management by Exception*) where human operators retain an immediate veto and one-touch control reclamation at every level.

---

## Operationalized Human-Subject Protection

NeuralEyeTracker translates neuroethics and neurorights (mental privacy, cognitive liberty, protection against neuro-discrimination) into concrete system mechanisms:

* **Calibrated Deceleration:** When working-memory saturation is detected, the interface introduces *constructive friction*—throttling non-critical alerts, decluttering visual layers, and enforcing brief micro-pauses before high-consequence confirmations to restore reflective System-2 reasoning.
* **Cognitive Compliance Auditing:** Continuously audits the adaptive system itself rather than grading the human worker. If operator acceptance rates exceed 95% without meaningful visual inspection, the audit flags emerging cognitive laziness and recalibrates automation thresholds.
* **Local Edge Sovereignty:** Raw video frames are processed transiently in memory and discarded immediately after feature extraction; personalized calibration weights remain strictly local under the user's sole control, with instant cryptographic erasure and reset capabilities.

---

## Repository Architecture

```text
NeuralEyeTracker/
├── config/                     # Measurement parameters, calibration grids, detector weights, and runtime profiles
├── core/                       # PupilDetector, EyeSegmenter, NeuralGazeModel, TrackerThread, Analyzer, ReportGenerator
├── ui/                         # PyQt5 desktop views, live telemetry dashboards, and calibration interfaces
├── utils/                      # Input validation, data sanitization, and formatting utilities
├── resources/                  # Static desktop assets and visual resources
├── stimuli/                    # Categorized affective visual stimulus sets
│   ├── neutral/                # Baseline neutral visual stimuli
│   ├── positive/               # Positively valenced stimuli
│   ├── negative/               # Negatively valenced stimuli
│   ├── threat/                 # Threatening / hazard-related stimuli
│   └── trauma/                 # Trauma-related stimuli
├── packaging/                  # Application packaging definitions
├── installer/                  # Installer configuration and distribution assets
├── Docs/                       # Technical documentation and visual branding (Docs/logo.png)
└── web/                        # React + TypeScript + Vite web companion interface
    └── src/                    # Frontend source modules
```

---

<div align="center">

  <strong>NeuralEyeTracker</strong><br />
  <sub>Adaptive Neurocognitive Architectures — Tokaj-Hegyalja University</sub>

</div>