import gym
import rospy
import roslaunch
import time
import numpy as np
import cv2

from gym import utils, spaces
from cv_bridge import CvBridge, CvBridgeError

from gym_gazebo.envs import gazebo_env
from gazebo_msgs.msg import ModelState
from gazebo_msgs.srv import GetModelState, SetModelState

from geometry_msgs.msg import Twist
from std_srvs.srv import Empty
from sensor_msgs.msg import Image, LaserScan

from gym.utils import seeding


# Images size
witdh = 640
center_image = witdh/2

# Coord X ROW
x_row = [260, 360, 450]
# Maximum distance from the line
RANGES = [300, 280, 250]  # Line 1, 2 and 3

RESET_RANGE = [-40, 40]

# Deprecated?
space_reward = np.flip(np.linspace(0, 1, 300))

last_center_line = 0

class ImageF1:
    def __init__(self):
        self.height = 3  # Image height [pixels]
        self.width = 3  # Image width [pixels]
        self.timeStamp = 0  # Time stamp [s] */
        self.format = ""  # Image format string (RGB8, BGR,...)
        self.data = np.zeros((self.height, self.width, 3), np.uint8)  # The image data itself
        self.data.shape = self.height, self.width, 3

    def __str__(self):
        s = "Image: {\n   height: " + str(self.height) + "\n   width: " + str(self.width)
        s = s + "\n   format: " + self.format + "\n   timeStamp: " + str(self.timeStamp)
        return s + "\n   data: " + str(self.data) + "\n}"


class GazeboF1QlearnCameraEnv(gazebo_env.GazeboEnv):

    def __init__(self):
        # Launch the simulation with the given launchfile name
        gazebo_env.GazeboEnv.__init__(self, "F1Cameracircuit_v0.launch")
        self.vel_pub = rospy.Publisher('/F1ROS/cmd_vel', Twist, queue_size=5)
        self.unpause = rospy.ServiceProxy('/gazebo/unpause_physics', Empty)
        self.pause = rospy.ServiceProxy('/gazebo/pause_physics', Empty)
        self.reset_proxy = rospy.ServiceProxy('/gazebo/reset_simulation', Empty)

        self.action_space = spaces.Discrete(3)  # F,L,R
        self.reward_range = (-np.inf, np.inf)
        print("\n\n\n ------ CREANDO ENTORNO ------ \n\n\n")
        self._seed()

    def discretize_observation(self, data, new_ranges):

        discretized_ranges = []
        min_range = 0.05
        done = False
        mod = len(data.ranges)/new_ranges
        new_data = data.ranges[10:-10]
        for i, item in enumerate(new_data):
            if i % mod == 0:
                if data.ranges[i] == float('Inf') or np.isinf(data.ranges[i]):
                    discretized_ranges.append(6)
                elif np.isnan(data.ranges[i]):
                    discretized_ranges.append(0)
                else:
                    discretized_ranges.append(int(data.ranges[i]))
            if min_range > data.ranges[i] > 0:
                #print("Data ranges: {}".format(data.ranges[i]))
                done = True
                break

            #print("LECTURA --> {}".format(data.ranges[12]))


        return discretized_ranges, done


    def imageMsg2Image(self, img, cv_image):

        image = ImageF1()
        image.width = img.width
        image.height = img.height
        image.format = "RGB8"
        image.timeStamp = img.header.stamp.secs + (img.header.stamp.nsecs *1e-9)
        image.data = cv_image

        return image


    def get_center(self, image_line):

        try:
            coords = np.divide(np.max(np.nonzero(image_line)) - np.min(np.nonzero(image_line)), 2)
            coords = np.min(np.nonzero(image_line)) + coords
        except:
            coords = -1

        return coords


    def processed_image(self, img):

        """
        Convert img to HSV. Get the image processed. Get 3 lines from the image.

        :parameters: input image 640x480
        :return: x, y, z: 3 coordinates
        """

        img_proc = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        line_pre_proc = cv2.inRange(img_proc, (0, 30, 30), (0, 255, 200))

        # gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(line_pre_proc, 240, 255, cv2.THRESH_BINARY)

        line_1 = mask[x_row[0], :]
        line_2 = mask[x_row[1], :]
        line_3 = mask[x_row[2], :]

        central_1 = self.get_center(line_1)
        central_2 = self.get_center(line_2)
        central_3 = self.get_center(line_3)

        # print(central_1, central_2, central_3)

        return [central_1, central_2, central_3]


    def calculate_observation(self, data):
        min_range = 0.5  # Default: 0.21
        done = False
        for i, item in enumerate(data.ranges):
            if min_range > data.ranges[i] > 0:
                done = True
        return done


    def get_center_of_laser(self, data):

        laser_len = len(data.ranges)
        left_sum = sum(data.ranges[laser_len - (laser_len / 5):laser_len - (laser_len / 10)])  # 80-90
        right_sum = sum(data.ranges[(laser_len / 10):(laser_len / 5)])  # 10-20

        center_detour = (right_sum - left_sum) / 5

        return center_detour

    def _seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]







    def step(self, action):
        rospy.wait_for_service('/gazebo/unpause_physics')
        try:
            self.unpause()
        except (rospy.ServiceException) as e:
            print("/gazebo/unpause_physics service call failed")

        if action == 0:  # FORWARD
            vel_cmd = Twist()
            vel_cmd.linear.x = 3
            vel_cmd.angular.z = 0.0
            self.vel_pub.publish(vel_cmd)
        elif action == 1:  # LEFT
            vel_cmd = Twist()
            vel_cmd.linear.x = 3  # 0.05
            vel_cmd.angular.z = 1  # 0.3
            self.vel_pub.publish(vel_cmd)
        elif action == 2:  # RIGHT
            vel_cmd = Twist()
            vel_cmd.linear.x = 3  # 0.05
            vel_cmd.angular.z = -1  # -0.3
            # Get camera info

        image_data = None
        while image_data is None:
                image_data = rospy.wait_for_message('/F1ROS/cameraL/image_raw', Image, timeout=5)
                # Transform the image data from ROS to CVMat
                cv_image = CvBridge().imgmsg_to_cv2(image_data, "bgr8")
                f1_image_camera = self.imageMsg2Image(image_data, cv_image)

        rospy.wait_for_service('/gazebo/pause_physics')
        try:
            #resp_pause = pause.call()
            self.pause()
        except (rospy.ServiceException) as e:
            print("/gazebo/pause_physics service call failed")

        state = self.processed_image(image_data)






        done = False
        if abs(state[3]) > 2:
            done = True
        #print("center: {}".format(center_detour))

        # 3 actions
        # if not done:
        #     if abs(center_detour) < 2:
        #          reward = 1 / float(center_detour + 1)
        #     else:  # L or R no looping
        #          reward = 0.5 / float(center_detour + 1)
        # else:
        #     reward = -200

        if not done:
            if action == 0:
                reward = 5
            else:
                reward = 1
        else:
            reward = -200





        return state, reward, done, {}


    def reset(self):

        # Resets the state of the environment and returns an initial observation.
        rospy.wait_for_service('/gazebo/reset_simulation')
        try:
            #reset_proxy.call()
            self.reset_proxy()
            self.unpause()
        except (rospy.ServiceException) as e:
            print("/gazebo/reset_simulation service call failed")

        # Unpause simulation to make observation
        rospy.wait_for_service('/gazebo/unpause_physics')
        try:
            #resp_pause = pause.call()
            self.unpause()
        except (rospy.ServiceException) as e:
            print("/gazebo/unpause_physics service call failed")

        # Get camera info
        image_data = None
        while image_data is None:
            image_data = rospy.wait_for_message('/F1ROS/cameraL/image_raw', Image, timeout=5)
            # Transform the image data from ROS to CVMat
            cv_image = CvBridge().imgmsg_to_cv2(image_data, "bgr8")
            f1_image_camera = self.imageMsg2Image(image_data, cv_image)

        rospy.wait_for_service('/gazebo/pause_physics')
        try:
            #resp_pause = pause.call()
            self.pause()
        except (rospy.ServiceException) as e:
            print("/gazebo/pause_physics service call failed")
        state = self.processed_image(image_data)
        return state