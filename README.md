# Caricature Drawing Robot 🤖✏️

Turn your **Dobot Magician Lite** into an automated caricature and line-art drawing robot! This project takes any image (JPG, PNG, WEBP, etc.), processes it into optimized single-line strokes, and automatically sends the movements to the robotic arm to draw it on paper.

## Features
- **Smart Image Processing**: Automatically detects edges and converts photos to continuous line paths.
- **Native macOS File Picker**: Simple click-to-select image uploading.
- **Guided Calibration**: Easy terminal wizard to calibrate paper corners and pen heights (Z-axis).
- **Auto G-Code Generation**: Seamlessly maps image pixels to the physical canvas size of your Dobot arm.
- **Path Previewing**: Automatically shows you exactly what the robot will draw before it moves.

---

## 🚀 Setup & Installation

### 1. Requirements
- Python 3.8+
- [Dobot Magician Lite](https://www.dobot.cc/dobot-magician-lite.html) plugged in via USB.
- Mac / Linux / Windows (macOS recommended for native file picker).

### 2. Clone the Repository
```bash
git clone https://github.com/RoboX2020/caricature-drawing-robot.git
cd caricature-drawing-robot
```

### 3. Create a Virtual Environment & Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🎮 How to Use

1. **Start the Application**
   ```bash
   python main.py
   ```
   *The script will automatically detect and connect to your Dobot arm.*

2. **Calibrate the Robot (Press `C`)**
   The wizard will guide you to set 4 points:
   - **Pen DOWN height**: Where the pen touches the paper.
   - **Pen UP height**: A safe height for moving between strokes.
   - **Bottom-Left Corner**: The bottom-left of your paper.
   - **Top-Right Corner**: The top-right of your paper.

3. **Load an Image (Press `I`)**
   - Use the native file picker to select an image.
   - Choose a detail level (1 = minimal lines, 5 = maximum detail).
   - The app will map the image to your calibrated canvas and generate a preview!

4. **Draw (Press `D`)**
   - Sit back and watch the Dobot draw your photo! 
   - Need to stop? Just hit `Ctrl+C` for an emergency stop (the pen will automatically lift).

---

## 🛠 Project Structure
- `main.py`: The interactive terminal interface and workflow wizard.
- `dobot_controller.py`: Handles connection, safe serial communication, and Z-axis movements.
- `image_processor.py`: OpenCV logic for Canny edge detection, contours, and path optimization.
- `gcode_generator.py`: Converts optimized paths into raw G-Code/coordinates for the arm.
- `config.py`: Saves and loads your calibration settings.
