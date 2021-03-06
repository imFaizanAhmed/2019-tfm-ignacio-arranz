import time
import datetime
import pickle

import gym
import liveplot
import gym_gazebo
import numpy as np
from gym import wrappers
from qlearn import QLearn

import agents.f1.settings as settings


def render():
    render_skip = 0  # Skip first X episodes.
    render_interval = 50  # Show render Every Y episodes.
    render_episodes = 10  # Show Z episodes every rendering.

    if (episode % render_interval == 0) and (episode != 0) and (episode > render_skip):
        env.render()
    elif ((episode - render_episodes) % render_interval == 0) and (episode != 0) and (episode > render_skip) and \
            (render_episodes < episode):
        env.render(close=True)


def load_model(qlearn, file_name):

    qlearn_file = open("./logs/qlearn_models/" + file_name)
    model = pickle.load(qlearn_file)

    qlearn.q = model
    qlearn.alpha = settings.algorithm_params["alpha"]
    qlearn.gamma = settings.algorithm_params["gamma"]
    qlearn.epsilon = settings.algorithm_params["epsilon"]
    # highest_reward = settings.algorithm_params["highest_reward"]

    print("\n\nMODEL LOADED. Number of (action, state): {}".format(len(model)))
    print("    - Loading:    {}".format(file_name))
    print("    - Model size: {}".format(len(qlearn.q)))
    print("    - Action set: {}".format(settings.actions_set))
    print("    - Epsilon:    {}".format(qlearn.epsilon))
    print("    - Start:      {}".format(datetime.datetime.now()))


def save_model(current_time, states, states_counter, states_rewards):
    # Tabular RL: Tabular Q-learning basically stores the policy (Q-values) of  the agent into a matrix of shape
    # (S x A), where s are all states, a are all the possible actions. After the environment is solved, just save this
    # matrix as a csv file. I have a quick implementation of this on my GitHub under Reinforcement Learning.

    # Q TABLE
    base_file_name = "_act_set_{}_epsilon_{}".format(settings.actions_set, round(qlearn.epsilon, 2))
    file_dump = open("./logs/qlearn_models/1_" + current_time + base_file_name + '_QTABLE.pkl', 'wb')
    pickle.dump(qlearn.q, file_dump)
    # STATES COUNTER
    states_counter_file_name = base_file_name + "_STATES_COUNTER.pkl"
    file_dump = open("./logs/qlearn_models/2_" + current_time + states_counter_file_name, 'wb')
    pickle.dump(states_counter, file_dump)
    # STATES CUMULATED REWARD
    states_cum_reward_file_name = base_file_name + "_STATES_CUM_REWARD.pkl"
    file_dump = open("./logs/qlearn_models/3_" + current_time + states_cum_reward_file_name, 'wb')
    pickle.dump(states_rewards, file_dump)
    # STATES
    steps = base_file_name + "_STATES_STEPS.pkl"
    file_dump = open("./logs/qlearn_models/4_" + current_time + steps, 'wb')
    pickle.dump(states, file_dump)


def save_times(checkpoints):
    file_name = "actions_"
    file_dump = open("./logs/" + file_name + settings.actions_set + '_checkpoints.pkl', 'wb')
    pickle.dump(checkpoints, file_dump)


####################################################################################################################
# MAIN PROGRAM
####################################################################################################################
if __name__ == '__main__':

    print(settings.title)
    print(settings.description)
    print("    - Start hour: {}".format(datetime.datetime.now()))

    environment = settings.envs_params["nurburgring"]
    env = gym.make(environment["env"])

    outdir = './logs/f1_qlearn_gym_experiments/'
    stats = {}  # epoch: steps
    states_counter = {}
    states_reward = {}

    env = gym.wrappers.Monitor(env, outdir, force=True)
    plotter = liveplot.LivePlot(outdir)

    last_time_steps = np.ndarray(0)

    actions = range(env.action_space.n)

    counter = 0
    estimate_step_per_lap = environment["estimated_steps"]
    lap_completed = False
    total_episodes = 20000
    epsilon_discount = 0.9986  # Default 0.9986

    qlearn = QLearn(actions=actions, alpha=0.8, gamma=0.9, epsilon=0.99)

    if settings.load_model:
        # file_name = 'qlearn_camera_solved/montreal/2/1_20200928_2303_act_set_simple_epsilon_0.87_QTABLE.pkl'
        file_name = 'qlearn_camera_solved/points_1_actions_simple__simple_circuit/4/1_20200921_2024_act_set_simple_epsilon_0.83_QTABLE.pkl'
        load_model(qlearn, file_name)
        highest_reward = max(qlearn.q.values(), key=stats.get)
    else:
        highest_reward = 0
    initial_epsilon = qlearn.epsilon

    telemetry_start_time = time.time()
    start_time = datetime.datetime.now()
    start_time_format = start_time.strftime("%Y%m%d_%H%M")

    print(settings.lets_go)

    previous = datetime.datetime.now()
    checkpoints = []  # "ID" - x, y - time

    # START ############################################################################################################
    for episode in range(total_episodes):

        counter = 0
        done = False
        lap_completed = False

        cumulated_reward = 0
        observation = env.reset()

        if qlearn.epsilon > 0.05:
            qlearn.epsilon *= epsilon_discount

        state = ''.join(map(str, observation))

        for step in range(500000):

            counter += 1

            # Pick an action based on the current state
            action = qlearn.selectAction(state)

            # Execute the action and get feedback
            observation, reward, done, info = env.step(action)
            cumulated_reward += reward

            if highest_reward < cumulated_reward:
                highest_reward = cumulated_reward

            nextState = ''.join(map(str, observation))

            try:
                states_counter[nextState] += 1
            except KeyError:
                states_counter[nextState] = 1

            qlearn.learn(state, action, reward, nextState)

            env._flush(force=True)

            if settings.save_positions:
                now = datetime.datetime.now()
                if now - datetime.timedelta(seconds=3) > previous:
                    previous = datetime.datetime.now()
                    x, y = env.get_position()
                    checkpoints.append([len(checkpoints), (x, y), datetime.datetime.now().strftime('%M:%S.%f')[-4]])

                if datetime.datetime.now() - datetime.timedelta(minutes=3, seconds=12) > start_time:
                    print("Finish. Saving parameters . . .")
                    save_times(checkpoints)
                    env.close()
                    exit(0)

            if not done:
                state = nextState
            else:
                last_time_steps = np.append(last_time_steps, [int(step + 1)])
                stats[int(episode)] = step
                states_reward[int(episode)] = cumulated_reward
                break

            if step > estimate_step_per_lap and not lap_completed:
                lap_completed = True
                if settings.plotter_graphic:
                    plotter.plot_steps_vs_epoch(stats, save=True)
                save_model(start_time_format, stats, states_counter, states_reward)
                print("\n\n====> LAP COMPLETED in: {} - Epoch: {} - Cum. Reward: {} <====\n\n".format(
                        datetime.datetime.now() - start_time,
                        episode,
                        cumulated_reward
                    )
                )

            if counter > 1000:
                if settings.plotter_graphic:
                    plotter.plot_steps_vs_epoch(stats, save=True)
                qlearn.epsilon *= epsilon_discount
                save_model(start_time_format, episode, states_counter, states_reward)
                print("\t- epsilon: {}\n\t- cum reward: {}\n\t- dict_size: {}\n\t- time: {}\n\t- steps: {}\n".format(
                    round(qlearn.epsilon, 2), cumulated_reward, len(qlearn.q), datetime.datetime.now()-start_time, step))
                counter = 0

            if datetime.datetime.now() - datetime.timedelta(hours=2) > start_time:
                print(settings.eop)
                save_model(start_time_format, stats, states_counter, states_reward)
                print("    - N epoch:     {}".format(episode))
                print("    - Model size:  {}".format(len(qlearn.q)))
                print("    - Action set:  {}".format(settings.actions_set))
                print("    - Epsilon:     {}".format(round(qlearn.epsilon, 2)))
                print("    - Cum. reward: {}".format(cumulated_reward))

                env.close()
                exit(0)
            # print("Obser: {} - Rew: {}".format(observation, reward))

        if episode % 1 == 0 and settings.plotter_graphic:
            # plotter.plot(env)
            plotter.plot_steps_vs_epoch(stats)
            # plotter.full_plot(env, stats, 2)  # optional parameter = mode (0, 1, 2)

        if episode % 250 == 0 and settings.save_model and episode > 1:
            print("\nSaving model . . .\n")
            save_model(start_time_format, stats, states_counter, states_reward)

        m, s = divmod(int(time.time() - telemetry_start_time), 60)
        h, m = divmod(m, 60)

        print("\nEP: {} - epsilon: {} - Reward: {} - Time: {} - Steps: {}\n".format(
                episode + 1,
                round(qlearn.epsilon, 2),
                cumulated_reward,
                start_time_format,
                step
            )
        )

    print("Total EP: {} - epsilon: {} - ep. discount: {} - Highest Reward: {}".format(
            total_episodes,
            initial_epsilon,
            epsilon_discount,
            highest_reward
        )
    )

    l = last_time_steps.tolist()
    l.sort()

    # print("Parameters: a="+str)
    print("Overall score: {:0.2f}".format(last_time_steps.mean()))
    print("Best 100 score: {:0.2f}".format(reduce(lambda x, y: x + y, l[-100:]) / len(l[-100:])))

    plotter.plot_steps_vs_epoch(stats, save=True)

    env.close()
