# WavyOS


| ![mascot.png](./avatar/assets/avatar.png) | 
|:--:| 
| *Wavy* |

> An intelligent assistant for Windows OS that combines deep automation of routine tasks, AI-powered voice control, and emotional interaction through a graphical avatar.

**Our mission** is to reduce the cognitive load on users when interacting with a PC and personalize the OS experience.

---

## ✨ Features

* **Voice Activation & Control:** Wake Word activation, real-time speech-to-text recognition (STT), and text-to-speech output (TTS).
* **Intelligent AI Brain:** Processing complex and off-script user queries through LLM integration (OpenAI).
* **Smart Automation & OS Interaction:** Modifying audio/network settings, managing processes, emptying the Recycle Bin, and cleaning the "Downloads" folder.
* **Computer Vision:** Fast screen capturing, window analysis, and simulation of user actions (clicks, hotkeys).
* **Graphical Interface:** An interactive overlay app avatar developed using the modern Qt framework.

---

## 🏗️ Project Architecture & Thread Model

WavyOS utilizes a **multithreaded and asynchronous architecture within a single OS process**. This ensures that heavy AI workloads (such as STT/TTS and LLM processing) run concurrently in background worker threads without freezing or degrading the performance of the graphical user interface.

### Module Distribution & Concurrency
1. **Main Thread (UI, Tray & Settings):**
   * Manages the **PySide6** Qt event loop to render the avatar overlay and settings dashboard.
   * Handles user interactions, window rendering, and UI animations.
2. **Background Worker Threads (`threading` & `asyncio`):**
   * Host the resource-heavy voice processing stack (`RealtimeSTT` and speech synthesis).
   * Asynchronously execute Windows API, PowerShell tasks, and custom automation scripts.

### Inter-Thread Communication (ITC)
The communication between the voice recognition core, the command processor, and the GUI layer is handled via thread-safe internal queues (**`queue.Queue`**). Detected voice triggers and commands are placed into the queue by background threads and consumed by the UI layer to update Wavy's emotional state and trigger corresponding Qt animations.

---

## 🛠️ Tech Stack

The project is developed exclusively for the **Windows** ecosystem.

### 💻 Graphical Interface
* **`PySide6`** — A modern graphical shell (Qt) for rendering the avatar and management windows.

### 🧠 Artificial Intelligence & Speech Technologies
* **STT (Speech-to-Text):** `RealtimeSTT`, `faster-whisper`, `webrtcvad-wheels`, `scipy`
* **Wake Word (Voice Activation):** `openwakeword`, `pvporcupine`
* **TTS (Text-to-Speech):** `realtimetts` (supporting Piper, Edge, gTTS), `soundfile`
* **LLM (Language Model):** `openai`, `pydantic`
* **Computations:** `torch`, `torchaudio`, `numpy`

### ⚙️ OS Automation & Computer Vision
* **Windows Integration:** `pywin32`, `psutil`, `pycaw`, `subprocess`, `Send2Trash`, `keyboard`
* **Screen Analysis & GUI:** `opencv-python`, `mss`, `pillow`, `pyscreeze`, `pyautogui`
* **Web Automation:** `Playwright`

---

## 🚀 Getting Started

### Prerequisites
Before installation, ensure that your Windows environment meets the following requirement:
1. **Python 3.11+**

### Installation & Launch

1. Clone the project repository:
   ```bash
   git clone https://github.com/ilyamikhailov16/WavyOS.git
   cd WavyOS
   ```

2. Install all dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Launch the application:
   ```bash
   python main.py
   ```

---

## 💻 Usage Examples

The assistant operates continuously in real-time, executing spoken commands directly without a hotword.

Examples:

* *«Сделай скриншот»*
* *«Открой Калькулятор*
* *«Очисти корзину»*
* *«Выключи звук»*
* *«Закрой браузер»*
