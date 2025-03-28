import sys
import speech_recognition as sr
import psutil
import subprocess
import platform
import time  # Add time import
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QPushButton, QLabel, QTextEdit, QComboBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import os

class VoiceThread(QThread):
    command_received = pyqtSignal(str)
    status_update = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.wake_word = "hey chanti"
        self.is_running = True
        self.microphone = None
        self.is_listening_for_command = False
        self.process_manager = ProcessManager()
        
        # Much more sensitive recognition settings
        self.recognizer.energy_threshold = 300  # Even lower threshold for better sensitivity
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.1  # More responsive to changes
        self.recognizer.dynamic_energy_ratio = 1.2  # More sensitive to quieter sounds
        self.recognizer.pause_threshold = 0.5  # Shorter pause threshold
        self.recognizer.phrase_threshold = 0.1  # Lower phrase threshold
        self.recognizer.non_speaking_duration = 0.3  # Shorter non-speaking duration
        
    def normalize_text(self, text):
        """Normalize detected text for better matching"""
        # Common misrecognitions and their corrections
        corrections = {
            'hmt': 'hey',
            'hint': 'hey',
            'hand': 'hey',
            'hnd': 'hey',
            'mt': 'hey',
            'hey chandi': 'hey chanti',
            'hey shanty': 'hey chanti',
            'hey shanti': 'hey chanti',
            'hey chunti': 'hey chanti',
            'hey chante': 'hey chanti',
            'hey chantee': 'hey chanti',
            'hey chanthi': 'hey chanti',
            'hey chanty': 'hey chanti',
            'hey shunty': 'hey chanti',
            'hey chunty': 'hey chanti',
            'hey chuntu': 'hey chanti',
            'a chanti': 'hey chanti',
            'hey chandi': 'hey chanti'
        }
        
        # First, try exact matches
        for wrong, correct in corrections.items():
            if wrong in text:
                text = text.replace(wrong, correct)
        
        # Then, try to fix partial matches
        words = text.split()
        if len(words) >= 2:
            # If we see something like 'hmt chanti', convert it to 'hey chanti'
            if words[0] in ['hmt', 'hint', 'hand', 'hnd', 'mt']:
                words[0] = 'hey'
            # If we see 'chandi', 'shanty', etc. as the second word, convert to 'chanti'
            if words[1] in ['chandi', 'shanty', 'shanti', 'chunti', 'chante', 'chantee', 'chanthi', 'chanty', 'shunty', 'chunty', 'chuntu']:
                words[1] = 'chanti'
            text = ' '.join(words)
        
        return text.strip()
        
    def run(self):
        try:
            # Use a lower sample rate for better performance
            self.microphone = sr.Microphone(sample_rate=16000)
            with self.microphone as source:
                print("Please wait - Calibrating microphone for background noise...")
                # Shorter initial calibration but more frequent adjustments
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                initial_energy = self.recognizer.energy_threshold
                print(f"Microphone calibrated. Energy threshold: {initial_energy}")
                print("\nListening for wake word 'Hey Chanti'... (speak clearly and at a normal pace)")
                
                while self.is_running:
                    try:
                        # Clear audio buffer
                        if hasattr(self.recognizer, '_audio_buffer'):
                            self.recognizer._audio_buffer = []
                        
                        # Adjust noise level more frequently
                        if not self.is_listening_for_command:
                            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                        
                        # Different timeouts for wake word and command
                        if not self.is_listening_for_command:
                            print("Listening...")
                            audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=3)
                        else:
                            print("Listening for command... (you have 5 seconds)")
                            audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                        
                        try:
                            text = self.recognizer.recognize_google(
                                audio,
                                language='en-US',
                                show_all=False
                            ).lower().strip()
                            
                            # Normalize the detected text
                            normalized_text = self.normalize_text(text)
                            print(f"Detected: {text}")
                            if text != normalized_text:
                                print(f"Normalized to: {normalized_text}")
                            
                            # Check for wake word
                            if not self.is_listening_for_command:
                                if "hey chanti" in normalized_text:
                                    print("\n🎤 Wake word detected!")
                                    # Quick recalibration
                                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                                    # Play notification sound
                                    self.process_manager.play_notification()
                                    print("Please speak your command... (you have 5 seconds)")
                                    self.is_listening_for_command = True
                                    # Adjust energy threshold for command
                                    self.recognizer.energy_threshold = max(initial_energy * 0.8, 300)
                            # If we are listening for a command, process it
                            else:
                                if text.strip():  # If there's any text detected
                                    print(f"Processing command: {text}")
                                    self.command_received.emit(text)
                                    self.is_listening_for_command = False  # Reset state
                                    print("\nListening for wake word 'Hey Chanti'...")
                            
                            del audio  # Clean up audio data
                            
                        except sr.UnknownValueError:
                            # If we're listening for a command and get silence, reset after a few attempts
                            if self.is_listening_for_command:
                                print("No command detected, please try again or say 'Hey Chanti' for a new command")
                                self.is_listening_for_command = False
                        except sr.RequestError as e:
                            print(f"❌ Error with the speech recognition service; {e}")
                            self.is_listening_for_command = False
                            
                    except sr.WaitTimeoutError:
                        # If we're in command mode and get a timeout, reset
                        if self.is_listening_for_command:
                            print("Command timeout. Please say 'Hey Chanti' and try again.")
                            self.is_listening_for_command = False
                        continue
                        
        except Exception as e:
            print(f"❌ Critical error in voice thread: {e}")
        finally:
            if self.microphone:
                del self.microphone
            if hasattr(self.recognizer, '_audio_buffer'):
                self.recognizer._audio_buffer = []
                
    def stop(self):
        print("Stopping voice recognition...")
        self.is_running = False
        self.is_listening_for_command = False
        if hasattr(self.recognizer, '_audio_buffer'):
            self.recognizer._audio_buffer = []
        self.wait()

class ProcessManager:
    def __init__(self):
        self.mac_app_names = {
            'chrome': 'Google Chrome',
            'safari': 'Safari',
            'firefox': 'Firefox',
            'terminal': 'Terminal',
            'notes': 'Notes',
            'calculator': 'Calculator',
            'system preferences': 'System Preferences',
            'settings': 'System Settings',
            'mail': 'Mail',
            'messages': 'Messages',
            'calendar': 'Calendar',
            'photos': 'Photos',
            'music': 'Music',
            'maps': 'Maps',
            'finder': 'Finder',
            'preview': 'Preview',
            'textedit': 'TextEdit',
            'activity monitor': 'Activity Monitor',
            'app store': 'App Store',
            'facetime': 'FaceTime',
            'keynote': 'Keynote',
            'pages': 'Pages',
            'numbers': 'Numbers'
        }
        self.system_info = {}
        self.common_websites = {
            'gmail': 'https://mail.google.com',
            'youtube': 'https://www.youtube.com',
            'google': 'https://www.google.com',
            'maps': 'https://maps.google.com',
            'drive': 'https://drive.google.com',
            'calendar': 'https://calendar.google.com',
            'github': 'https://github.com',
            'linkedin': 'https://linkedin.com',
            'amazon': 'https://amazon.com',
            'netflix': 'https://netflix.com'
        }
        self.update_system_info()

    def update_system_info(self):
        self.system_info = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'battery': psutil.sensors_battery() if hasattr(psutil, 'sensors_battery') else None,
            'disk_usage': psutil.disk_usage('/').percent
        }

    def speak(self, text):
        if platform.system() == 'Darwin':  # macOS
            subprocess.run(['say', text])
        else:
            print(text)  # Fallback to print for other platforms
        
    def start_process(self, process_name):
        try:
            process_name = process_name.lower()
            if platform.system() == 'Darwin':  # macOS
                # Try to find the proper app name
                app_name = self.mac_app_names.get(process_name, process_name)
                subprocess.Popen(['open', '-a', app_name])
                self.speak(f"Started {app_name} successfully")
            elif platform.system() == 'Windows':
                subprocess.Popen(process_name)
                self.speak(f"Started {process_name} successfully")
            else:  # Linux
                subprocess.Popen(process_name)
                self.speak(f"Started {process_name} successfully")
            return True
        except Exception as e:
            self.speak(f"Failed to start {process_name}. Please make sure the application name is correct.")
            return False
            
    def stop_process(self, process_name):
        process_name = process_name.lower()
        if platform.system() == 'Darwin':
            app_name = self.mac_app_names.get(process_name, process_name)
        else:
            app_name = process_name
            
        for proc in psutil.process_iter(['name']):
            try:
                if app_name.lower() in proc.info['name'].lower():
                    proc.kill()
                    self.speak(f"Stopped {app_name} successfully")
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        self.speak(f"Could not find process {app_name}")
        return False
        
    def list_processes(self):
        processes = []
        access_denied_count = 0
        no_such_process_count = 0
        try:
            # Get all process info at once
            for proc in psutil.process_iter(['name', 'pid', 'username', 'memory_percent', 'cpu_percent']):
                try:
                    pinfo = proc.info
                    # Format memory and CPU usage to 2 decimal places
                    mem_usage = f"{pinfo['memory_percent']:.2f}%" if pinfo['memory_percent'] else "N/A"
                    cpu_usage = f"{pinfo['cpu_percent']:.1f}%" if pinfo['cpu_percent'] is not None else "N/A"
                    # Create a formatted string with process info
                    proc_info = f"{pinfo['name']} (PID: {pinfo['pid']}, User: {pinfo['username']}, CPU: {cpu_usage}, Memory: {mem_usage})\n{'─' * 80}"  # Add separator line
                    processes.append(proc_info)
                except psutil.AccessDenied:
                    access_denied_count += 1
                    continue
                except psutil.NoSuchProcess:
                    no_such_process_count += 1
                    continue
                except (KeyError, Exception) as e:
                    print(f"Error processing process info: {e}")
                    continue
            
            # Sort processes by name for better readability
            processes.sort()
            
            # Add summary information with more visible separation
            summary = [
                "═" * 80,  # Top border
                f"Total visible processes: {len(processes)}",
                f"Access denied processes: {access_denied_count}",
                f"Terminated during query: {no_such_process_count}",
                "═" * 80,  # Bottom border
                ""  # Empty line for spacing
            ]
            
            return summary + processes
        except Exception as e:
            print(f"Error listing processes: {e}")
            return ["Error: Could not retrieve process list"]

    def set_volume(self, level):
        """Set system volume (0-100)"""
        try:
            if platform.system() == 'Darwin':
                # Convert 0-100 to 0-10 for macOS
                vol = min(10, max(0, int(level * 0.1)))
                subprocess.run(['osascript', '-e', f'set volume output volume {level}'])
                self.speak(f"Volume set to {level} percent")
            else:
                self.speak("Volume control is only supported on macOS")
        except Exception as e:
            self.speak("Failed to set volume")

    def get_system_stats(self):
        """Get system statistics"""
        self.update_system_info()
        stats = []
        stats.append(f"CPU usage: {self.system_info['cpu_percent']}%")
        stats.append(f"Memory usage: {self.system_info['memory_percent']}%")
        stats.append(f"Disk usage: {self.system_info['disk_usage']}%")
        if self.system_info['battery']:
            stats.append(f"Battery: {self.system_info['battery'].percent}%")
        return stats

    def focus_app(self, app_name):
        """Bring application to front"""
        try:
            if platform.system() == 'Darwin':
                app_name = self.mac_app_names.get(app_name.lower(), app_name)
                subprocess.run(['osascript', '-e', f'tell application "{app_name}" to activate'])
                self.speak(f"Focused {app_name}")
                return True
        except Exception as e:
            self.speak(f"Could not focus {app_name}")
            return False

    def set_brightness(self, level):
        """Set screen brightness (0-100)"""
        try:
            if platform.system() == 'Darwin':  # macOS
                # Convert percentage to decimal (0-1)
                brightness = max(0, min(100, level)) / 100.0
                
                # First try using brightness control script
                script = '''
                tell application "System Events"
                    tell process "SystemUIServer"
                        try
                            set value of first slider of first menu bar item of menu bar 1 whose description contains "brightness" to %f
                        end try
                    end tell
                end tell
                ''' % brightness
                
                try:
                    subprocess.run(['osascript', '-e', script], check=True)
                    self.speak(f"Brightness set to {level} percent")
                    return
                except subprocess.CalledProcessError:
                    # If the first method fails, try the alternative method
                    pass

                # Alternative method: Use brightness keys
                current_brightness = 0
                try:
                    # Get current brightness using system_profiler
                    output = subprocess.check_output(['system_profiler', 'SPDisplaysDataType']).decode()
                    for line in output.split('\n'):
                        if 'Brightness' in line:
                            try:
                                current_brightness = float(line.split(':')[1].strip().rstrip('%'))
                            except (IndexError, ValueError):
                                current_brightness = 50  # Default to middle if can't determine
                except:
                    current_brightness = 50  # Default to middle if can't determine

                # Calculate how many steps to move
                steps = abs(int((level - current_brightness) / 6.25))  # Each press changes ~6.25%
                
                if level > current_brightness:
                    # Increase brightness
                    for _ in range(steps):
                        subprocess.run(['osascript', '-e', 'tell application "System Events" to key code 144'])
                        time.sleep(0.1)
                else:
                    # Decrease brightness
                    for _ in range(steps):
                        subprocess.run(['osascript', '-e', 'tell application "System Events" to key code 145'])
                        time.sleep(0.1)
                
                self.speak(f"Brightness adjusted to approximately {level} percent")
            else:
                self.speak("Brightness control is only supported on macOS")
        except Exception as e:
            print(f"Error setting brightness: {e}")
            self.speak("Failed to control brightness")

    def adjust_brightness(self, direction):
        """Adjust brightness up or down"""
        try:
            if platform.system() == 'Darwin':  # macOS
                key_code = 144 if direction == "up" else 145  # 144 for up, 145 for down
                # Press the key multiple times for more noticeable change
                for _ in range(4):  # 4 steps for more noticeable change
                    subprocess.run(['osascript', '-e', f'tell application "System Events" to key code {key_code}'])
                    time.sleep(0.1)  # Small delay between key presses
                self.speak(f"Brightness {direction}")
        except Exception as e:
            print(f"Error adjusting brightness: {e}")
            self.speak(f"Failed to adjust brightness {direction}")

    def play_notification(self):
        """Play a notification sound"""
        try:
            if platform.system() == 'Darwin':  # macOS
                # Try different notification sounds in order of preference
                sound_paths = [
                    '/System/Library/Sounds/Tink.aiff',  # Short and crisp
                    '/System/Library/Sounds/Pop.aiff',   # Alternative
                    '/System/Library/Sounds/Glass.aiff'  # Fallback
                ]
                
                for sound_path in sound_paths:
                    if subprocess.run(['test', '-f', sound_path]).returncode == 0:
                        subprocess.run(['afplay', sound_path])
                        break
                else:
                    # If no sound files found, use system beep
                    subprocess.run(['osascript', '-e', 'beep'])
        except Exception as e:
            print(f"Could not play notification sound: {e}")
            # Fallback to system beep
            subprocess.run(['tput', 'bel'])

    def system_control(self, action):
        """Control system actions like sleep, shutdown, restart, etc."""
        try:
            if platform.system() == 'Darwin':  # macOS
                if action == "sleep":
                    subprocess.run(['pmset', 'sleepnow'])
                    self.speak("Putting computer to sleep")
                elif action == "restart":
                    self.speak("Restarting computer")
                    subprocess.run(['osascript', '-e', 'tell app "System Events" to restart'])
                elif action == "shutdown":
                    self.speak("Shutting down computer")
                    subprocess.run(['osascript', '-e', 'tell app "System Events" to shut down'])
                elif action == "lock":
                    subprocess.run(['pmset', 'displaysleepnow'])
                    self.speak("Locking screen")
                elif action == "night mode":
                    script = '''
                    tell application "System Events"
                        tell appearance preferences
                            set dark mode to not dark mode
                        end tell
                    end tell
                    '''
                    subprocess.run(['osascript', '-e', script])
                    self.speak("Toggled night mode")
        except Exception as e:
            print(f"Error in system control: {e}")
            self.speak(f"Failed to {action} system")

    def take_screenshot(self, type="full"):
        """Take a screenshot"""
        try:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            desktop_path = os.path.expanduser("~/Desktop")
            screenshot_path = os.path.join(desktop_path, f"screenshot_{timestamp}.png")
            
            if type == "full":
                subprocess.run(['screencapture', screenshot_path])
                self.speak("Took full screenshot")
            elif type == "selection":
                subprocess.run(['screencapture', '-i', screenshot_path])
                self.speak("Took screenshot of selection")
            elif type == "window":
                subprocess.run(['screencapture', '-w', screenshot_path])
                self.speak("Took screenshot of active window")
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            self.speak("Failed to take screenshot")

    def open_website(self, site_name):
        """Open a website in the default browser"""
        try:
            site_name = site_name.lower()
            if site_name in self.common_websites:
                url = self.common_websites[site_name]
                subprocess.run(['open', url])
                self.speak(f"Opening {site_name}")
            else:
                # Try to open as direct URL if it ends with .com, .org, etc.
                if any(site_name.endswith(tld) for tld in ['.com', '.org', '.net', '.edu']):
                    url = f"https://{site_name}"
                    subprocess.run(['open', url])
                    self.speak(f"Opening {site_name}")
                else:
                    self.speak(f"Website {site_name} not found in known websites")
        except Exception as e:
            print(f"Error opening website: {e}")
            self.speak(f"Failed to open {site_name}")

    def switch_to_app(self, app_name):
        """Switch to a running application"""
        try:
            app_name = self.mac_app_names.get(app_name.lower(), app_name)
            script = f'''
            tell application "{app_name}"
                activate
            end tell
            '''
            subprocess.run(['osascript', '-e', script])
            self.speak(f"Switched to {app_name}")
        except Exception as e:
            print(f"Error switching app: {e}")
            self.speak(f"Failed to switch to {app_name}")

    def monitor_process(self, pid, threshold):
        try:
            process = psutil.Process(pid)
            cpu_percent = process.cpu_percent()
            mem_percent = process.memory_percent()
            if cpu_percent > threshold or mem_percent > threshold:
                self.speak(
                    f"Warning! Process {process.name()} is using "
                    f"{cpu_percent:.1f}% CPU and {mem_percent:.1f}% memory"
                )
        except:
            self.speak(f"Could not monitor PID {pid}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.process_manager = ProcessManager()
        self.voice_thread = None  # Initialize to None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('Voice Process Manager')
        self.setGeometry(100, 100, 600, 400)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Status label
        self.status_label = QLabel('Status: Ready')
        layout.addWidget(self.status_label)
        
        # Process list
        self.process_list = QTextEdit()
        self.process_list.setReadOnly(True)
        layout.addWidget(self.process_list)
        
        # Command input
        self.command_input = QComboBox()
        self.command_input.setEditable(True)
        self.command_input.addItems(['start chrome', 'stop notepad', 'list processes'])
        layout.addWidget(self.command_input)
        
        # Buttons
        self.start_button = QPushButton('Start Voice Recognition')
        self.start_button.clicked.connect(self.toggle_voice_recognition)
        layout.addWidget(self.start_button)
        
        self.refresh_button = QPushButton('Refresh Process List')
        self.refresh_button.clicked.connect(self.refresh_process_list)
        layout.addWidget(self.refresh_button)
        
        # Initial process list
        self.refresh_process_list()
        
    def toggle_voice_recognition(self):
        if not self.voice_thread or not self.voice_thread.is_running:
            self.voice_thread = VoiceThread()
            self.voice_thread.command_received.connect(self.handle_voice_command)
            self.voice_thread.start()
            self.start_button.setText('Stop Voice Recognition')
            self.status_label.setText('Status: Listening for "Hey Chanti"')
        else:
            if self.voice_thread:
                self.voice_thread.stop()
                self.voice_thread = None
            self.start_button.setText('Start Voice Recognition')
            self.status_label.setText('Status: Ready')
            
    def refresh_process_list(self):
        processes = self.process_manager.list_processes()
        self.process_list.setText('\n'.join(processes))
        
    def handle_voice_command(self, command):
        self.status_label.setText(f'Status: Processing command: {command}')
        
        cmd_parts = command.lower().split()
        
        if not cmd_parts:
            self.process_manager.speak("No command received")
            return
            
        # Process Management Commands
        if cmd_parts[0] == 'kill' and len(cmd_parts) > 1:
            try:
                pid = int(cmd_parts[1])
                try:
                    process = psutil.Process(pid)
                    process_name = process.name()
                    process.terminate()
                    self.process_manager.speak(f"Terminated process {process_name} with PID {pid}")
                    time.sleep(1)  # Give process time to terminate
                    self.refresh_process_list()
                except psutil.NoSuchProcess:
                    self.process_manager.speak(f"No process found with PID {pid}")
                except psutil.AccessDenied:
                    self.process_manager.speak(f"Access denied when trying to terminate process with PID {pid}")
            except ValueError:
                self.process_manager.speak("Please provide a valid PID number")
        
        # Force Kill Command
        elif cmd_parts[0] == 'force' and cmd_parts[1] == 'kill' and len(cmd_parts) > 2:
            try:
                pid = int(cmd_parts[2])
                process = psutil.Process(pid)
                process_name = process.name()
                process.kill()  # SIGKILL instead of terminate
                self.process_manager.speak(f"Force killed process {process_name} with PID {pid}")
                self.refresh_process_list()
            except Exception as e:
                self.process_manager.speak(f"Failed to force kill process {pid}")
        
        # Kill Multiple PIDs
        elif cmd_parts[0] == 'kill' and cmd_parts[1] == 'pids' and len(cmd_parts) > 2:
            try:
                pids = [int(pid) for pid in cmd_parts[2:]]
                killed = []
                failed = []
                for pid in pids:
                    try:
                        process = psutil.Process(pid)
                        process_name = process.name()
                        process.terminate()
                        killed.append(f"{process_name}({pid})")
                    except:
                        failed.append(str(pid))
                if killed:
                    self.process_manager.speak(f"Terminated processes: {', '.join(killed)}")
                if failed:
                    self.process_manager.speak(f"Failed to terminate PIDs: {', '.join(failed)}")
                self.refresh_process_list()
            except ValueError:
                self.process_manager.speak("Please provide valid PID numbers")
        
        # Process Information
        elif cmd_parts[0] == 'info' and len(cmd_parts) > 1:
            try:
                pid = int(cmd_parts[1])
                process = psutil.Process(pid)
                info = [
                    f"Process: {process.name()}",
                    f"PID: {pid}",
                    f"Status: {process.status()}",
                    f"CPU: {process.cpu_percent()}%",
                    f"Memory: {process.memory_percent():.2f}%",
                    f"Created: {time.ctime(process.create_time())}",
                    f"User: {process.username()}"
                ]
                self.process_list.setText('\n'.join(info))
                self.process_manager.speak(f"Showing information for process {process.name()}")
            except:
                self.process_manager.speak(f"Could not get information for PID {pid}")
        
        # Search by Process Name
        elif cmd_parts[0] == 'find' and len(cmd_parts) > 1:
            search_term = ' '.join(cmd_parts[1:]).lower()
            matching_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent']):
                try:
                    if search_term in proc.info['name'].lower():
                        matching_processes.append(
                            f"{proc.info['name']} (PID: {proc.info['pid']}, "
                            f"User: {proc.info['username']}, "
                            f"Memory: {proc.info['memory_percent']:.2f}%)"
                        )
                except:
                    continue
            if matching_processes:
                self.process_list.setText('\n'.join(matching_processes))
                self.process_manager.speak(f"Found {len(matching_processes)} matching processes")
            else:
                self.process_manager.speak(f"No processes found matching '{search_term}'")
        
        # Resource Usage Monitor
        elif cmd_parts[0] == 'monitor' and len(cmd_parts) > 1:
            try:
                pid = int(cmd_parts[1])
                threshold = float(cmd_parts[2]) if len(cmd_parts) > 2 else 80.0
                process = psutil.Process(pid)
                cpu_percent = process.cpu_percent()
                mem_percent = process.memory_percent()
                if cpu_percent > threshold or mem_percent > threshold:
                    self.process_manager.speak(
                        f"Warning! Process {process.name()} is using "
                        f"{cpu_percent:.1f}% CPU and {mem_percent:.1f}% memory"
                    )
            except:
                self.process_manager.speak(f"Could not monitor PID {pid}")
                
        # System Control Commands
        elif cmd_parts[0] == 'sleep' or command == 'go to sleep':
            self.process_manager.system_control("sleep")
        elif cmd_parts[0] == 'restart':
            self.process_manager.system_control("restart")
        elif cmd_parts[0] == 'shutdown':
            self.process_manager.system_control("shutdown")
        elif cmd_parts[0] == 'lock' or command == 'lock screen':
            self.process_manager.system_control("lock")
        elif 'night mode' in command or 'dark mode' in command:
            self.process_manager.system_control("night mode")

        # Screenshot Commands
        elif 'screenshot' in command:
            if 'window' in command:
                self.process_manager.take_screenshot("window")
            elif 'selection' in command or 'area' in command:
                self.process_manager.take_screenshot("selection")
            else:
                self.process_manager.take_screenshot("full")

        # Website Commands
        elif cmd_parts[0] == 'open' and len(cmd_parts) > 1:
            if cmd_parts[1] == 'website':
                site_name = ' '.join(cmd_parts[2:])
            else:
                site_name = ' '.join(cmd_parts[1:])
            self.process_manager.open_website(site_name)

        # App Switching
        elif cmd_parts[0] == 'switch' and 'to' in command:
            app_name = command.split('to')[-1].strip()
            self.process_manager.switch_to_app(app_name)

        # Existing Commands
        elif cmd_parts[0] == 'start':
            process_name = ' '.join(cmd_parts[1:])
            self.process_manager.start_process(process_name)
        
        elif cmd_parts[0] == 'stop':
            process_name = ' '.join(cmd_parts[1:])
            self.process_manager.stop_process(process_name)
        
        elif cmd_parts[0] == 'focus':
            app_name = ' '.join(cmd_parts[1:])
            self.process_manager.focus_app(app_name)
        
        elif 'list' in command and 'process' in command:
            self.refresh_process_list()
            self.process_manager.speak("Here are the running processes")
        
        elif cmd_parts[0] == 'volume':
            try:
                level = int(cmd_parts[1])
                if 0 <= level <= 100:
                    self.process_manager.set_volume(level)
                else:
                    self.process_manager.speak("Volume level should be between 0 and 100")
            except (IndexError, ValueError):
                self.process_manager.speak("Please specify a volume level between 0 and 100")
            
        elif command == 'system stats':
            stats = self.process_manager.get_system_stats()
            self.process_list.setText('\n'.join(stats))
            self.process_manager.speak("Here are the current system statistics")
        
        elif cmd_parts[0] == 'brightness' or 'brightness' in command:
            # Handle various brightness commands
            if len(cmd_parts) > 1:
                if cmd_parts[1] == 'up' or 'increase' in command:
                    self.process_manager.adjust_brightness("up")
                elif cmd_parts[1] == 'down' or 'decrease' in command:
                    self.process_manager.adjust_brightness("down")
                elif cmd_parts[1] == 'maximum' or cmd_parts[1] == 'max' or 'full' in command:
                    self.process_manager.set_brightness(100)
                elif cmd_parts[1] == 'minimum' or cmd_parts[1] == 'min':
                    self.process_manager.set_brightness(0)
                else:
                    # Try to extract percentage from command
                    try:
                        # Remove '%' and 'percent' from the command if present
                        level_str = command.replace('%', '').replace('percent', '').strip()
                        # Extract the last number from the command
                        numbers = [int(s) for s in level_str.split() if s.isdigit()]
                        if numbers:
                            level = numbers[-1]  # Take the last number mentioned
                            if 0 <= level <= 100:
                                self.process_manager.set_brightness(level)
                            else:
                                self.process_manager.speak("Brightness level should be between 0 and 100 percent")
                        else:
                            self.process_manager.speak("Please specify a valid brightness level between 0 and 100 percent")
                    except ValueError:
                        self.process_manager.speak("Please specify a valid brightness level between 0 and 100 percent")
            else:
                self.process_manager.speak("Please specify brightness level. You can say: brightness up, down, maximum, minimum, or a number between 0 and 100 percent")
        
        elif command == 'help':
            help_text = [
                "Available commands:",
                "\n1. Application Control:",
                "   - 'start [app name]' - Launch an application",
                "   - 'stop [app name]' - Close an application",
                "   - 'focus [app name]' - Bring application to front",
                "   - 'switch to [app name]' - Switch to running application",
                "\n2. System Control:",
                "   - 'sleep' or 'go to sleep' - Put computer to sleep",
                "   - 'restart' - Restart computer",
                "   - 'shutdown' - Shutdown computer",
                "   - 'lock' or 'lock screen' - Lock the screen",
                "   - 'night mode' or 'dark mode' - Toggle dark mode",
                "\n3. Screenshots:",
                "   - 'screenshot' - Take full screenshot",
                "   - 'screenshot window' - Screenshot active window",
                "   - 'screenshot selection' - Screenshot selected area",
                "\n4. Websites:",
                "   - 'open [website]' - Open website (e.g., 'open gmail')",
                "\n5. Display Control:",
                "   - 'brightness up/down' - Adjust brightness",
                "   - 'brightness [0-100]' - Set specific brightness",
                "   - 'brightness maximum/minimum' - Set max/min brightness",
                "\n6. System Information:",
                "   - 'system stats' - Show system statistics",
                "   - 'list processes' - Show running processes",
                "\n7. Volume Control:",
                "   - 'volume [0-100]' - Set system volume",
                "\n8. Help:",
                "   - 'help' - Show this help message"
            ]
            self.process_list.setText('\n'.join(help_text))
            self.process_manager.speak("Showing available commands")
        
        else:
            self.process_manager.speak("I didn't understand that command. Say 'help' for available commands")
        
        self.status_label.setText('Status: Ready')
        
    def closeEvent(self, event):
        if self.voice_thread:
            self.voice_thread.stop()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 