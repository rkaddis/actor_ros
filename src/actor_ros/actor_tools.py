#!/usr/bin/env python3

# from dbw_polaris_msgs.msg import (  # Drive By Wire Messages
#     BrakeCmd,
#     BrakeReport,
#     Gear,
#     GearCmd,
#     GearReport,
#     SteeringCmd,
#     SteeringReport,
#     ThrottleCmd,
#     ThrottleReport,
# )
# from geometry_msgs.msg import Twist  # ROS Messages
# from std_msgs.msg import Bool, Empty, Float32, Float64, Int32, String, UInt8  # ROS Messages

# End of Imports --------------------------------------------------------------
#
#
#
#
#
# Start of Utilities ----------------------------------------------------------


from typing import Any


class ActorStatusReader:
    """ACTor Status Reader subscribes to ACTor status messages and stores the latest values.
    Use read_from_redis=True if running outside a ROS node"""

    def __init__(self, read_from_redis=False, simulate_for_testing=False):
        """Initialize the ACTor Status Message Reader"""

        self.simulating_values = simulate_for_testing

        self.is_simulated = False
        self.is_autonomous = False
        self.is_tele_operated = False
        self.accelerator_percent = 0
        self.brake_percent = 0
        self.steering_wheel_angle = 0
        self.road_angle = 0
        self.speed = 0
        self.gear = "NONE"
        self.heading = 0
        self.latitude = 0
        self.longitude = 0
        self.is_enabled = False
        self.requested_speed = 0
        self.requested_road_angle = 0
        self.estop_state = False
        self.estop_heartbeat = False
        self.estop_physical_button = False
        self.estop_wireless_button = False
        self.estop_software_button = False

        if self.simulating_values:
            self.simulate_values()

        else:
            if read_from_redis:  # In case status is read from a database, do not initialize the subscriber.
                # NOTE: updates need to be called manually using the redis_callback() function
                try:
                    self.connect_to_redis()
                except ConnectionError as e:
                    print(e)
                    return e

            else:  # Start a thread to continuously read status messages from ROS
                # NOTE: This requires the instance to be created inside a ROS node

                import rospy  # ROS Python API

                from actor_ros.msg import ActorStatus  # Custom ROS Message

                rospy.Subscriber(rospy.get_param("status"), ActorStatus, self.actor_status_callback, queue_size=1)
                # NOTE: param('status') accesed from the 'actor/' namespace by default

    def __call__(self):
        """Call method to update the latest ACTor Status values"""
        if self.simulating_values:
            self.simulate_values()
        else:
            if hasattr(self, "redis"):
                self.redis_callback()

    def __del__(self):
        """Cleanup method. Closes Redis connection"""
        if hasattr(self, "redis"):
            self.redis.close()

    def actor_status_callback(self, ActorStatus_msg) -> None:
        """Callback to get the latest ACTor Status message"""

        # States
        self.is_simulated = ActorStatus_msg.is_simulated
        self.is_autonomous = ActorStatus_msg.is_autonomous
        self.is_tele_operated = ActorStatus_msg.is_tele_operated

        # Hardware information
        self.accelerator_percent = ActorStatus_msg.accelerator_percent
        self.brake_percent = ActorStatus_msg.brake_percent
        self.steering_wheel_angle = ActorStatus_msg.steering_wheel_angle
        self.road_angle = ActorStatus_msg.road_angle
        self.speed = ActorStatus_msg.speed
        self.gear = ActorStatus_msg.gear
        self.heading = ActorStatus_msg.heading
        self.latitude = ActorStatus_msg.latitude
        self.longitude = ActorStatus_msg.longitude

        # Control information
        self.is_enabled = ActorStatus_msg.is_enabled
        self.requested_speed = ActorStatus_msg.requested_speed
        self.requested_road_angle = ActorStatus_msg.requested_road_angle

        # E-stop
        self.estop_state = ActorStatus_msg.estop_state
        self.estop_heartbeat = ActorStatus_msg.estop_heartbeat
        self.estop_physical_button = ActorStatus_msg.estop_physical_button
        self.estop_wireless_button = ActorStatus_msg.estop_wireless_button
        self.estop_software_button = ActorStatus_msg.estop_software_button

    def connect_to_redis(self) -> bool:
        """Connect to Redis server and read the latest ACTor Status values"""

        import time

        import redis  # Redis Key Value Store Python API

        attempts = 0
        max_attempts = 3
        while attempts < max_attempts:
            try:
                # Attempt to connect to Redis server run from the status node
                # NOTE: Using default settings for Redis. Change if required...
                self.redis = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
                time.sleep(2)  # Wait for 2 seconds for status node to start
                self.redis_callback()  # Read values from redis server once
                return True  # Connection successful
            except redis.ConnectionError as e:
                print(f"Failed to connect to Redis server: {e}")
                attempts += 1
                time.sleep(2)  # Wait for 2 seconds before retrying
        print("Failed to connect to Redis server after multiple attempts. Exiting.")
        raise ConnectionError("Failed to connect to Redis server after multiple attempts.")

    @staticmethod
    def to_bool(value: str) -> bool:
        """Converts string value to boolean"""
        if value is None:
            return False
        return value.lower() == "true"

    @staticmethod
    def to_float(value: str) -> float:
        """Converts string value to float"""
        return float(value) if value is not None else 0

    def redis_callback(self) -> None:
        """Callback to get the latest ACTor Status values from Redis server"""

        # Read values from redis server - NOTE: type conversion is needed since Redis stores values as strings
        self.is_simulated = self.to_bool(self.redis.get("is_simulated"))
        self.is_autonomous = self.to_bool(self.redis.get("is_autonomous"))
        self.is_tele_operated = self.to_bool(self.redis.get("is_tele_operated"))

        self.accelerator_percent = self.to_float(self.redis.get("accelerator_percent"))
        self.brake_percent = self.to_float(self.redis.get("brake_percent"))
        self.steering_wheel_angle = self.to_float(self.redis.get("steering_wheel_angle"))
        self.road_angle = self.to_float(self.redis.get("road_angle"))
        self.speed = self.to_float(self.redis.get("speed"))
        self.gear = self.redis.get("gear")
        self.heading = self.to_float(self.redis.get("heading"))
        self.latitude = self.to_float(self.redis.get("latitude"))
        self.longitude = self.to_float(self.redis.get("longitude"))

        self.is_enabled = self.to_bool(self.redis.get("is_enabled"))
        self.requested_speed = self.to_float(self.redis.get("requested_speed"))
        self.requested_road_angle = self.to_float(self.redis.get("requested_road_angle"))

        self.estop_state = self.to_bool(self.redis.get("estop_state"))
        self.estop_heartbeat = self.to_bool(self.redis.get("estop_heartbeat"))
        self.estop_physical_button = self.to_bool(self.redis.get("estop_physical_button"))
        self.estop_wireless_button = self.to_bool(self.redis.get("estop_wireless_button"))
        self.estop_software_button = self.to_bool(self.redis.get("estop_software_button"))

    def simulate_values(self) -> None:
        """Simulate variables for testing purposes. Used to test the GUI"""
        import random

        self.is_simulated = False
        self.is_autonomous = False
        self.is_tele_operated = False
        self.accelerator_percent = round(random.uniform(20, 80), 2)
        self.brake_percent = round(random.uniform(0, 50), 2)
        self.steering_wheel_angle = round(random.uniform(-600, 600), 2)
        self.road_angle = round(random.uniform(-37.5, 37.5), 2)
        self.speed = round(random.uniform(0, 15), 2)
        self.gear = random.choice(["PARK", "REVERSE", "NEUTRAL", "DRIVE"])
        self.is_enabled = True
        self.requested_speed = round(random.uniform(0, 15), 2)
        self.requested_road_angle = round(random.uniform(-37.5, 37.5), 2)

        self.estop_state = False
        self.estop_heartbeat = True
        self.estop_physical_button = False
        self.estop_wireless_button = False
        self.estop_software_button = False

        # NOTE: These values can be changed in desired way if needed

    # End of class ------------------------


class EStopManager:
    """Manager for E-Stop functionality. E-Stop can be triggered from anywhere.
    Also provides a way to reset a software E-Stop, enable and disable the Drive-By-Wire System."""

    # actor/estop/state - Bool
    # actor/estop/physical_button - Bool
    # actor/estop/wireless_button - Bool
    # actor/estop/trigger - Empty
    # actor/estop/reset - Empty
    # actor/estop/heartbeat_edge - Header
    # actor/estop/heartbeat_core - Header

    def __init__(self):
        """Initialize the E-Stop Manager for any script"""
        self.estop_topic = "/actor/estop/trigger"
        self.estop_reset_topic = "/actor/estop/reset"
        self.enable_topic = "/vehicle/enable"
        self.disable_topic = "/vehicle/disable"

    def __call__(self) -> bool:
        """Call method to trigger E-Stop using the instance of E-Stop Manager"""
        return self.trigger_estop()

    def trigger_estop(self) -> bool:
        """Trigger E-Stop by publishing an empty message to the E-Stop topic using rostopic pub command"""

        return self._send_command(f'rostopic pub --once {self.estop_topic} std_msgs/Empty "{{}}" >/dev/null 2>&1 &')

    def reset(self) -> bool:
        """Resets E-Stop by publishing an empty message to the E-Stop reset topic using rostopic pub command"""

        return self._send_command(
            f'rostopic pub --once {self.estop_reset_topic} std_msgs/Empty "{{}}" >/dev/null 2>&1 &'
        )

    def enable_dbw(self) -> bool:
        """Enables vehicle control using rostopic pub command"""

        return self._send_command(f'rostopic pub --once {self.enable_topic} std_msgs/Empty "{{}}" >/dev/null 2>&1 &')

    def disable_dbw(self) -> bool:
        """Disable vehicle control using rostopic pub command"""

        return self._send_command(f'rostopic pub --once {self.disable_topic} std_msgs/Empty "{{}}" >/dev/null 2>&1 &')

    def _send_command(self, command: str) -> str:
        """Send a custom shell command using system. Generally used with rostopic pub command"""
        import os

        try:
            os.system(command)
            return "Command sent successfully"
        except Exception as e:
            return f"Failed to send command: {e}"

    # End of class ------------------------


class ScriptPlayer:
    """Executes Python scripts as a subprocess."""

    def __init__(self, directory: str):
        """Initialize the Script Player"""
        self.active_directory = directory  # Full path to the directory
        self.file_list = ""

        self.selected_file = ""  # Name of the selected file with extension
        self.process = None
        self.is_running = False
        self.output_text = []
        self.process_return_code = ""

    def __del__(self):
        """Cleanup method"""
        self.stop_script()

    def load_files(self):
        """Make a list of files in the active directory"""
        import os

        self.file_list = [file for file in os.listdir(self.active_directory) if file.endswith(".py")]
        self.file_list.sort()
        self.selected_file = ""
        return "Directory loaded"

    def execute(self):
        """Execute the selected file in a separate process"""
        import os
        import subprocess
        from threading import Thread

        if self.is_running:
            return "A script is already running. Please stop it first."

        if self.selected_file == "":
            return "Please select a script to execute"

        # Set the running flag and Clear the output text to allow new output
        self.is_running = True
        self.output_text = ["initializing script..."]

        try:
            # NOTE: "rosrun actor_ros <script_name>" can be used, this will likely impact how logging and stdout works
            self.process = subprocess.Popen(
                [f"python3 -u {self.active_directory}{self.selected_file}"],
                shell=True,  # Needed to source ROS using .bashrc
                preexec_fn=os.setsid,  # Set process id of the new process group
                stdout=subprocess.PIPE,  # Captures print() output # NOTE: ROS logging should be used to maintain logs
                stderr=subprocess.STDOUT,  # Captures Raised Errors and Exceptions
                universal_newlines=True,
                text=True,
                # bufsize=1,
            )

            # Start a separate thread to monitor the process
            Thread(target=self.monitor_process, daemon=True).start()
            # Start a separate thread to read stdout and stderr streams
            Thread(target=self.read_output, daemon=True).start()

            return "Script started running"

        except Exception as e:
            self.is_running = False
            self.process = None
            return f"---------------- Error in script ----------------\n{e}"

    def monitor_process(self):
        """Monitor the process and gets the return code"""

        try:
            self.process_return_code = self.process.wait()
            self.is_running = False
            self.output_text.append(f"Script returncode: {self.process_return_code}")
        except Exception as e:
            print(f"---------------- Exception in monitor_process ----------------\n{e}")
            self.is_running = False

    def read_output(self):
        """Read output stream and add lines into output_text
        stream is direct input stream from stdout or stderr"""

        import os

        try:
            print(f"Process Group ID: {os.getpgid(self.process.pid)}")
            while self.process.poll() is None:
                line = self.process.stdout.readline()
                print(line, end="")  # Display the line in the shell
                line = line.rstrip("\n")  # Remove the newline character
                self.output_text.append(line)  # Store the line in the output_text list

            # When EOF is reached (process is terminated), set the running flag to False just in case
            self.is_running = False
        except Exception as e:
            print(f"---------------- Exception in read_output ----------------\n{e}")
            self.is_running = False

    def stop_script(self, timeout=0.5):
        """Stop the currently running script"""
        import os  # have to use os.killpg because subprocess spawns a shell with script as its child process
        import signal
        import time

        tmp_text = """
        --------------------------------------------------------
                           Terminating script...
        --------------------------------------------------------
        """
        self.output_text.append(tmp_text)
        print(tmp_text)

        if self.process and self.is_running:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)  # SIGTERM shell and its child processes
            time.sleep(timeout)

            if self.process is None:  # Process has been successfully terminated
                self.is_running = False
                return "Script stopped"

            try:
                if self.process.poll() is None:  # If process is still running
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)  # SIGKILL shell and its child processes
                    time.sleep(timeout)
                    self.is_running = False
                    self.process = None
                    return "Script stopped"

                else:
                    self.is_running = False
                    self.process = None
                    return "Script stopped"
            except Exception as e:
                self.is_running = False
                self.process = None
                return f"---------------- Error/Exception in script termination ----------------\n{e}"

        else:
            return "No script is currently running"

    # End of class ------------------------


class YAMLReader:
    """Read YAML files and store the data in an attribute style access object.
    This only reads at instance creation"""

    import os

    def __init__(self, file_path):
        """Initialize the YAML Reader"""
        import munch

        self.file_path = file_path
        self.params = munch.Munch()

    def read(self, file_path=None):
        import yaml
        from munch import munchify

        if file_path is None:
            file_path = self.file_path
        with open(file_path, "r") as file:
            try:
                print(f"Loading YAML file: {file_path}")
                self.params = munchify(yaml.safe_load(file))
            except Exception as e:
                print(f"Failed to load YAML file: {e}")

    def write(self, file_path=None):
        """Write the params attribute to a YAML file"""
        import yaml
        from munch import unmunchify

        if file_path is None:
            file_path = self.file_path
        if self.params is not None:
            try:
                with open(file_path, "w") as file:
                    yaml.safe_dump(unmunchify(self.params), file)
                    print(f"YAML file successfully written to: {file_path}")
            except Exception as e:
                print(f"Failed to write YAML file: {e}")
        else:
            print("No data to write")

    # End of class ------------------------


class RedisReader:
    """Read Key-Value pairs from Redis server"""

    def __init__(self):
        """Initialize the Redis Reader"""

        # Add Variables to read from Redis server -------------------------------------------------
        self.image_1 = None
        self.image_2 = None
        self.image_3 = None
        self.image_4 = None

        # -----------------------------------------------------------------------------------------

        try:
            self.connect_to_redis()
        except ConnectionError as e:
            print(e)
            return e

    def __call__(self):
        """Call method to update the latest values"""
        if hasattr(self, "redis"):
            self.redis_callback()

    def __del__(self):
        """Cleanup method. Closes Redis connection"""
        if hasattr(self, "redis"):
            self.redis.close()

    def connect_to_redis(self) -> bool:
        """Connect to Redis server"""

        import time

        import redis  # Redis Key Value Store Python API

        attempts = 0
        max_attempts = 3

        while attempts < max_attempts:
            try:
                # Attempt to connect to Redis server
                # NOTE: Using default settings for Redis. Change if required...
                self.redis = redis.Redis(host="localhost", port=6379, db=0, decode_responses=False)
                self.redis_callback()  # Read values from redis server once
                return True  # Connection successful
            except redis.ConnectionError as e:
                print(f"Failed to connect to Redis server: {e}")
                attempts += 1
                time.sleep(2)  # Wait for 2 seconds before retrying

        print("Failed to connect to Redis server after multiple attempts. Exiting.")
        raise ConnectionError("Failed to connect to Redis server after multiple attempts.")

    def redis_callback(self) -> None:
        """Callback to get the latest values from Redis server"""

        # Add Variables to read from Redis server -------------------------------------------------
        self.image_1 = self.to_pil_image(self.redis.get("image_1"))
        self.image_2 = self.to_pil_image(self.redis.get("image_2"))
        self.image_3 = self.to_pil_image(self.redis.get("image_3"))
        self.image_4 = self.to_pil_image(self.redis.get("image_4"))

        # -----------------------------------------------------------------------------------------
        # NOTE: type conversion is needed since Redis stores values as strings

    def to_pil_image(self, image_binary):
        """Convert Redis image byte string to PIL image"""
        import io

        from PIL import Image

        if image_binary is not None:
            return Image.open(io.BytesIO(image_binary))
        else:
            return None

    # End of class ------------------------
