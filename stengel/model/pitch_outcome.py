from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
import math

import numpy as np
import tensorflow as tf


class PitchOutcomeModel(object):
    num_numeric_inputs = 47
    num_outcomes = 5

    def __init__(self, batch_size=32, learning_rate=0.1, hidden_dim=96):
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.hidden_dim = hidden_dim
        self.graph = tf.Graph()
        self._build_graph()
        self.node_names = [node.name + ":0" for node in self.graph.as_graph_def().node]

    def _build_graph(self):
        with self.graph.as_default():
            # Define inputs
            pitch_data = tf.placeholder(tf.float32,
                                        shape=[self.batch_size, self.num_numeric_inputs],
                                        name="pitch_data")
            pitch_outcomes = tf.placeholder(tf.int32, shape=[self.batch_size],
                                            name="pitch_outcomes")

            hidden_weight = tf.Variable(tf.random_normal([self.num_numeric_inputs,
                                                          self.hidden_dim], stddev=0.3))
            hidden_bias = tf.Variable(tf.random_normal([self.hidden_dim], stddev=0.1))
            hidden_logits = tf.matmul(pitch_data, hidden_weight) + hidden_bias
            hidden_scores = tf.nn.sigmoid(hidden_logits)
            hidden_output = tf.nn.dropout(hidden_scores, 0.5)

            output_weight = tf.Variable(tf.random_normal([self.hidden_dim, self.num_outcomes],
                                                         stddev=0.5))
            output_bias = tf.Variable(tf.random_normal([self.num_outcomes], stddev=0.1))
            output_logits = tf.matmul(hidden_output, output_weight) + output_bias

            # Define loss
            cross_entropy = tf.nn.sparse_softmax_cross_entropy_with_logits(
                    labels=pitch_outcomes, logits=output_logits
            )
            self.loss = tf.reduce_mean(cross_entropy)
            self.optimizer = tf.train.AdagradOptimizer(self.learning_rate).minimize(self.loss)

    def fit(self, train_data, validation_data, training_steps=1000, print_every=200):
        with tf.Session(graph=self.graph) as session:
            tf.global_variables_initializer().run()
            for step in range(training_steps):
                input_dict = self.filter_input_dict(train_data.get_batch(self.batch_size))
                _, loss = session.run([self.optimizer, self.loss], feed_dict=input_dict)
                if not step % print_every:
                    print(step, self.score(session, validation_data))

    def score(self, session, data):
        scores = []
        while not data.has_reached_end():
            input_dict = self.filter_input_dict(data.get_batch(self.batch_size))
            loss = session.run([self.loss], feed_dict=input_dict)
            scores.append(loss)
        return math.exp(np.mean(scores))

    def filter_input_dict(self, input_dict):
        for k in input_dict.keys():
            if k not in self.node_names:
                del input_dict[k]
        return input_dict
