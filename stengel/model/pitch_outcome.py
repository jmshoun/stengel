from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
import math

import numpy as np
import tensorflow as tf


class PitchOutcomeModel(object):
    num_numeric_inputs = 47
    num_outcomes = 5

    def __init__(self, batch_size=32, learning_rate=0.1, hidden_nodes=[96],
                 num_batters=None, batter_embed_size=16,
                 num_pitchers=None, pitcher_embed_size=16):
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.hidden_nodes = hidden_nodes
        self.num_batters = num_batters
        self.batter_embed_size = batter_embed_size
        self.num_pitchers = num_pitchers
        self.pitcher_embed_size = pitcher_embed_size
        self.graph = tf.Graph()
        with self.graph.as_default():
            self._build_graph()
        self.session = tf.Session(graph=self.graph)
        self.node_names = [node.name + ":0" for node in self.graph.as_graph_def().node]
        self.initialized = False

    def _build_graph(self):
        data, outcomes = self._build_inputs()
        hidden_outputs = [self._build_hidden_layer(data, self.hidden_nodes[0])]
        for num_nodes in self.hidden_nodes[1:]:
            hidden_outputs.append(self._build_hidden_layer(hidden_outputs[-1], num_nodes))
        logit_output = self._build_output_layer(hidden_outputs[-1])
        self.loss = self._build_loss(logit_output, outcomes)
        self.optimizer = tf.train.AdagradOptimizer(self.learning_rate).minimize(self.loss)

    def _build_inputs(self):
        pitch_data = tf.placeholder(tf.float32, shape=[self.batch_size, self.num_numeric_inputs],
                                    name="pitch_data")
        pitch_outcomes = tf.placeholder(tf.int32, shape=[self.batch_size], name="pitch_outcomes")
        inputs = [pitch_data]
        if self.num_batters:
            inputs.append(self._build_batter_input())
        if self.num_pitchers:
            inputs.append(self._build_pitcher_input())
        final_input = tf.concat(inputs, 1)
        return final_input, pitch_outcomes

    def _build_batter_input(self):
        batter_ids = tf.placeholder(tf.int32, shape=[self.batch_size], name="batter_ids")
        batter_embedding = tf.Variable(tf.random_normal([self.num_batters,
                                                         self.batter_embed_size]))
        batter_embedded = tf.nn.embedding_lookup(batter_embedding, batter_ids)
        return batter_embedded

    def _build_pitcher_input(self):
        pitcher_ids = tf.placeholder(tf.int32, shape=[self.batch_size], name="pitcher_ids")
        pitcher_embedding = tf.Variable(tf.random_normal([self.num_pitchers,
                                                          self.pitcher_embed_size]))
        pitcher_embedded = tf.nn.embedding_lookup(pitcher_embedding, pitcher_ids)
        return pitcher_embedded

    @staticmethod
    def _build_hidden_layer(hidden_input, hidden_nodes):
        input_dim = hidden_input.get_shape().as_list()
        hidden_weight = tf.Variable(tf.random_normal([input_dim[1], hidden_nodes], stddev=0.05))
        hidden_bias = tf.Variable(tf.random_normal([hidden_nodes], stddev=0.1))
        hidden_logits = tf.matmul(hidden_input, hidden_weight) + hidden_bias
        hidden_scores = tf.nn.sigmoid(hidden_logits)
        hidden_output = tf.nn.dropout(hidden_scores, 0.5)
        return hidden_output

    def _build_output_layer(self, input_):
        input_dim = input_.get_shape().as_list()
        output_weight = tf.Variable(tf.random_normal([input_dim[1], self.num_outcomes],
                                                     stddev=0.05))
        output_bias = tf.Variable(tf.random_normal([self.num_outcomes], stddev=0.1))
        output_logits = tf.matmul(input_, output_weight) + output_bias
        return output_logits

    @staticmethod
    def _build_loss(prediction, outcome):
        cross_entropy = tf.nn.sparse_softmax_cross_entropy_with_logits(
            labels=outcome, logits=prediction)
        loss = tf.reduce_mean(cross_entropy)
        return loss

    def train(self, train_data, validation_data, training_steps=1000, print_every=200):
        with self.graph.as_default():
            if not self.initialized:
                self.session.run(tf.global_variables_initializer())
                self.initialized = True
            current_step = 0
            while current_step < training_steps:
                self._train_steps(train_data, print_every)
                current_step += print_every
                print("{:>7} - {:0.4f}".format(current_step, round(self.score(validation_data), 4)))

    def _train_steps(self, train_data, num_steps):
        for _ in range(num_steps):
            input_dict = self.filter_input_dict(train_data.get_batch(self.batch_size))
            _, loss = self.session.run([self.optimizer, self.loss], feed_dict=input_dict)

    def score(self, data):
        scores = []
        while not data.has_reached_end():
            input_dict = self.filter_input_dict(data.get_batch(self.batch_size))
            loss = self.session.run([self.loss], feed_dict=input_dict)
            scores.append(loss)
        return math.exp(np.mean(scores))

    def filter_input_dict(self, input_dict):
        for k in input_dict.keys():
            if k not in self.node_names:
                del input_dict[k]
        return input_dict
