import time

import gym
import gym_gazebo
import numpy as np
from gym import logger, wrappers

from f1_qlearn import QLearn
import liveplot


def render():
    render_skip = 0  # Skip first X episodes.
    render_interval = 50  # Show render Every Y episodes.
    render_episodes = 10  # Show Z episodes every rendering.

    if (episode % render_interval == 0) and (episode != 0) and (episode > render_skip):
        env.render()
    elif ((episode - render_episodes) % render_interval == 0) and (episode != 0) and (episode > render_skip) and \
            (render_episodes < episode):
        env.render(close=True)


# Save Model:
# Tabular RL: Tabular Q-learning basically stores the policy (Q-values) of 
# the agent into a matrix of shape (S x A), where s are all states, a are all
# the possible actions. After the environment is solved, just save this matri
# as a csv file. I have a quick implementation of this on my GitHub under 
# Reinforcement Learning.


####################################################################################################################
# MAIN PROGRAM
####################################################################################################################
if __name__ == '__main__':
    # GazeboF1QlearnLaserEnv-v0
    # GazeboF1QlearnCameraEnv-v0
    env = gym.make('GazeboF1QlearnCameraEnv-v0')
    outdir = './logs/f1_qlearn_gym_experiments/'

    env = gym.wrappers.Monitor(env, outdir, force=True)
    plotter = liveplot.LivePlot(outdir)

    last_time_steps = np.ndarray(0)

    actions = range(env.action_space.n)
    qlearn = QLearn(actions=actions, alpha=0.2, gamma=0.9, epsilon=0.99)

    initial_epsilon = qlearn.epsilon

    epsilon_discount = 0.9996  # Default 0.9986

    start_time = time.time()
    total_episodes = 20000
    highest_reward = 0
    
    for episode in range(total_episodes):

        done = False
        cumulated_reward = 0  # Should going forward give more reward then L/R ?
        
        observation = env.reset()

        if qlearn.epsilon > 0.05:
            qlearn.epsilon *= epsilon_discount

        # render() #defined above, not env.render()

        state = ''.join(map(str, observation))

        for i in range(1500):

            # Pick an action based on the current state
            action = qlearn.selectAction(state)

            # Execute the action and get feedback
            observation, reward, done, info = env.step(action)
            cumulated_reward += reward

            if highest_reward < cumulated_reward:
                highest_reward = cumulated_reward

            nextState = ''.join(map(str, observation))

            qlearn.learn(state, action, reward, nextState)

            env._flush(force=True)

            if not done:
                state = nextState
            else:
                last_time_steps = np.append(last_time_steps, [int(i + 1)])
                break

        if episode % 100 == 0:
            plotter.plot(env)
            print("\nQVALUES\n-------\n")
            print("LEN Qvalues: {}\n".format(len(qlearn.q)))
            print(qlearn.q)

        m, s = divmod(int(time.time() - start_time), 60)
        h, m = divmod(m, 60)
        print ("EP: " + str(episode + 1) + " - [alpha: " + str(round(qlearn.alpha, 2)) + " - gamma: " + str(
            round(qlearn.gamma, 2)) + " - epsilon: " + str(round(qlearn.epsilon, 2)) + "] - Reward: " + str(
            cumulated_reward) + "     Time: %d:%02d:%02d" % (h, m, s))

        # Github table content
    print ("\n|" + str(total_episodes) + "|" + str(qlearn.alpha) + "|" + str(qlearn.gamma) + "|" + str(
        initial_epsilon) + "*" + str(epsilon_discount) + "|" + str(highest_reward) + "| PICTURE |")

    l = last_time_steps.tolist()
    l.sort()

    # print("Parameters: a="+str)
    print("Overall score: {:0.2f}".format(last_time_steps.mean()))
    print("Best 100 score: {:0.2f}".format(reduce(lambda x, y: x + y, l[-100:]) / len(l[-100:])))

    env.close()
