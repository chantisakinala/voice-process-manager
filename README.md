# Voice Process Manager

A powerful voice-controlled process management application that allows you to control your computer using voice commands. Built with Python and PyQt5, this application provides a user-friendly interface for managing processes, controlling system settings, and executing various system commands through voice recognition.

## Features

### Voice Control
- Wake word detection ("Hey Chanti")
- Natural language command processing
- Real-time voice recognition
- Background noise adaptation

### Process Management
- Start and stop applications
- List running processes
- Monitor process resource usage
- Force kill processes
- Process information display

### System Control
- Sleep, restart, and shutdown commands
- Screen locking
- Night mode toggle
- Volume control
- Brightness adjustment
- Screenshot capture (full screen, window, or selection)

### Website Management
- Quick access to common websites
- Custom website opening
- Predefined website shortcuts (Gmail, YouTube, Google, etc.)

### System Monitoring
- Real-time CPU usage monitoring
- Memory usage tracking
- Battery status (if available)
- Disk usage information

## Requirements

- Python 3.6 or higher
- PyQt5
- SpeechRecognition
- psutil
- PyAudio

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/voice-process-manager.git
cd voice-process-manager
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python voice_process_manager.py
```

## Usage

1. Launch the application
2. Click "Start Voice Recognition" to begin listening
3. Say "Hey Chanti" to activate the voice assistant
4. Speak your command clearly
5. Wait for the command to be processed

### Available Commands

#### Application Control
- "start [app name]" - Launch an application
- "stop [app name]" - Close an application
- "focus [app name]" - Bring application to front
- "switch to [app name]" - Switch to running application

#### System Control
- "sleep" or "go to sleep" - Put computer to sleep
- "restart" - Restart computer
- "shutdown" - Shutdown computer
- "lock" or "lock screen" - Lock the screen
- "night mode" or "dark mode" - Toggle dark mode

#### Screenshots
- "screenshot" - Take full screenshot
- "screenshot window" - Screenshot active window
- "screenshot selection" - Screenshot selected area

#### Websites
- "open [website]" - Open website (e.g., "open gmail")

#### Display Control
- "brightness up/down" - Adjust brightness
- "brightness [0-100]" - Set specific brightness
- "brightness maximum/minimum" - Set max/min brightness

#### System Information
- "system stats" - Show system statistics
- "list processes" - Show running processes

#### Volume Control
- "volume [0-100]" - Set system volume

#### Help
- "help" - Show available commands

## Platform Support

- Windows
- macOS
- Linux (basic functionality)

## Troubleshooting

1. **Microphone not working**
   - Ensure your microphone is properly connected and set as the default input device
   - Check system permissions for microphone access
   - Try adjusting the energy threshold in the code if voice detection is too sensitive

2. **Voice recognition issues**
   - Ensure you have a stable internet connection (required for Google Speech Recognition)
   - Speak clearly and at a normal pace
   - Check if the wake word "Hey Chanti" is being detected properly

3. **Process management errors**
   - Run the application with appropriate permissions
   - Check if the process names are correct for your operating system

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Speech Recognition API for voice processing
- PyQt5 for the graphical interface
- psutil for system monitoring 