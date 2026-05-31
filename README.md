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

## 🏗️ Project Architecture & Concurrency

WavyOS uses a **multithreaded and asynchronous architecture** within a single OS process to keep the graphical interface smooth during heavy AI workloads.

* **Main Thread (UI & Tray):** Runs the **PySide6** event loop, rendering the avatar overlay, settings window, and animations.
* **Worker Threads (`threading` & `asyncio`):** Run the voice processing stack (`RealtimeSTT` / TTS) and execute Windows API or PowerShell automation scripts in the background.
* **Inter-Thread Communication:** Background threads push recognized commands into a thread-safe internal queue (**`queue.Queue`**), where the UI layer consumes them to instantly update the avatar's emotional state.

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
