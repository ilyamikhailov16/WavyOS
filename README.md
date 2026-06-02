# WavyOS


| ![mascot.png](./wavy/avatar/assets/avatar.png) | 
|:--:| 
| *Wavy* |

> An intelligent assistant for Windows OS that combines deep automation of routine tasks, AI-powered voice control, and emotional interaction through a graphical avatar.

**Our mission** is to reduce the cognitive load on users when interacting with a PC and personalize the OS experience.

---

## ✨ Features

* **Voice Activation & Control:** Real-time speech-to-text recognition (STT), and text-to-speech output (TTS).
* **Smart Automation & OS Interaction:** Modifying audio/network settings, managing processes, emptying the Recycle Bin, and cleaning the "Downloads" folder.
* **Computer Vision:** Fast screen capturing, window analysis, and simulation of user actions (clicks, hotkeys).
* **Avatar:** An interactive overlay app avatar developed using the Tkinter library.

---

## 🏗️ Project Architecture & Concurrency

WavyOS uses a **multithreaded and asynchronous architecture** within three OS processes to keep the graphical interface smooth during heavy AI workloads.

### Processes:
* **Core:** Listens to user commands and orchestrates other modules.
* **GUI:** Runs the **PySide6** event loop, rendering the avatar overlay, settings window, and animations.
* **Tray:** Runs the **pystray** event loop.
* **Inter-Process Communication:** Implemented using ZeroMQ.

### Threads:
* **Worker Threads (`threading` & `asyncio`):** Run the voice processing stack (`RealtimeSTT` / TTS) and execute Windows API or PowerShell automation scripts in the background.
* **Inter-Thread Communication:** Background threads push recognized commands into a thread-safe internal queue (**`queue.Queue`**), where the UI layer consumes them to instantly update the avatar's emotional state.

---

## 🛠️ Tech Stack

The project is developed exclusively for the **Windows** ecosystem.

### 🧑‍🍳 Multiprocessing
* **ZeroMQ** — a high-performance asynchronous messaging library designed for building scalable, distributed, and concurrent systems.

### 💻 Graphical Interface
* **`PySide6`** — A modern graphical shell (Qt) for rendering the avatar and management windows.

### 🧠 Artificial Intelligence & Speech Technologies
* **STT (Speech-to-Text):** `RealtimeSTT`, `faster-whisper`, `webrtcvad-wheels`, `scipy`
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
   python launcher.py
   ```

---

## 💻 Usage Examples

The assistant operates continuously in real-time, executing spoken commands directly.

Examples:

* *«Сделай скриншот»*
* *«Открой Калькулятор*
* *«Очисти корзину»*
* *«Выключи звук»*
* *«Закрой браузер»*
