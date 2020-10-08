import os
import time
import datetime
import pickle

import gym
import gym_gazebo
import numpy as np
from gym import wrappers
from qlearn import QLearn

import agents.f1.settings as settings


def save_poses(checkpoints, completed, output_dir, experiment, circuit, number, start_time, tested_on):
    lap_time = str(datetime.datetime.now() - start_time)
    if completed:
        file_name = "5_checkpoints_" + experiment + "_" + number + '_tested_on_' + tested_on + "_time_" + lap_time + '.pkl'
    else:
        file_name = "5_NO_COMPLETED_" + experiment + "_" + number + '_tested_on_' + tested_on + "_time_" + lap_time + '.pkl'

    file_dump = open(os.path.join(output_dir, circuit, experiment, number) + "/" + file_name, 'wb')
    pickle.dump(checkpoints, file_dump)
    print("Saved in: {}".format(os.path.join(output_dir, circuit, experiment, number) + "/" + file_name))


def load_model(actions, input_dir, circuit, experiment, number):

    path = os.path.join(input_dir, circuit, experiment, number)
    q_table_path_file = os.path.join(path, sorted(os.listdir(path))[0])

    qlearn_file = open(os.path.join(q_table_path_file))
    model = pickle.load(qlearn_file)

    qlearn = QLearn(actions=actions, alpha=0.2, gamma=0.9, epsilon=0.05)
    qlearn.q = model

    print("\n\n-----------------------\nMODEL LOADED: {}\n-----------------------\n\n".format(qlearn_file))

    return qlearn

####################################################################################################################
# MAIN PROGRAM
####################################################################################################################
if __name__ == '__main__':

    print(settings.title)
    print(settings.description)
    print("    - Start hour: {}".format(datetime.datetime.now()))

    environment = settings.envs_params["simple"]
    env = gym.make(environment["env"])

    input_dir = './logs/qlearn_models/qlearn_camera_solved'
    circuit = 'nurburgring'
    experiment = '3_point__actions_set__hard'
    number = '1'
    tested_on = 'simple_circuit'

    actions = range(env.action_space.n)

    last_time_steps = np.ndarray(0)
    counter = 0
    highest_reward = 0
    epsilon_discount = 0.98  # Default 0.9986
    stimate_step_per_lap = 4000
    lap_completed = False
    total_episodes = 5

    qlearn = load_model(actions, input_dir, circuit, experiment, number)

    telemetry_start_time = time.time()

    completed = False
    checkpoints = []

    print(settings.lets_go)

    for episode in range(total_episodes):
        start_time = datetime.datetime.now()
        previous = datetime.datetime.now()

        counter = 0
        done = False
        lap_completed = False

        cumulated_reward = 0  # Should going forward give more reward then L/R z?

        observation = env.reset()
        state = ''.join(map(str, observation))

        for step in range(500000):

            now = datetime.datetime.now()
            counter += 1

            # Pick an action based on the current state
            action = qlearn.selectAction(state)

            # Execute the action and get feedback
            observation, reward, done, info = env.step(action)
            cumulated_reward += reward

            if highest_reward < cumulated_reward:
                highest_reward = cumulated_reward

            nextState = ''.join(map(str, observation))
            # qlearn.learn(state, action, reward, nextState)
            # env._flush(force=True)

            if not done:
                state = nextState
                x, y = env.get_position()
            else:
                print("\n ---> Try: {}/{}\n".format(episode+1, total_episodes))
                last_time_steps = np.append(last_time_steps, [int(step + 1)])
                break

            if now - datetime.timedelta(seconds=3) > previous:
                previous = datetime.datetime.now()
                x, y = env.get_position()
                checkpoints.append([len(checkpoints), (x, y), datetime.datetime.now().strftime('%M:%S.%f')[-4]])

            if env.finish_line() and datetime.datetime.now() - datetime.timedelta(seconds=10) > start_time:
                completed = True
                print(settings.race_completed)
                save_poses(checkpoints, completed, input_dir, experiment, circuit, number, start_time, tested_on)
                print("    - N epoch:     {}".format(episode + 1))
                print("    - Action set:  {}".format(settings.actions_set))
                print("    - Cum. reward: {}".format(cumulated_reward))
                print("    - Time:        {}".format(datetime.datetime.now() - start_time))

                env.close()
                exit(0)

    print("TOO MANY ATTEMPTS. NO SUCCESS")

    save_poses(checkpoints, completed, input_dir, experiment, circuit, number, start_time, tested_on)

    env.close()
    exit(0)
