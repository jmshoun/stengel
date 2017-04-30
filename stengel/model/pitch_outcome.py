import math
import datetime
import functools

import numpy as np
import tensorflow as tf


class PitchOutcomeModel(object):
    """Model of pitch outcomes (ball, called strike, fair contact, etc.)

    Attributes:
        batch_size: Batch size for use in model fitting.
        learning_rate: Learning rate passed to the optimizer.
        dropout_rate: Dropout rate for hidden layers.
        hidden_nodes: List of ints; each element is the number of nodes in the ith hidden layer.
        num_batters: Number of unique batter IDs in the input data. If None, batter embeddings
            will not be used in the model.
        batter_embed_size: Dimension of the embedding vector for each batter.
        num_pitchers: Number of unique pitcher IDs in the input data. If None, pitcher
            embeddings will not be used in the model.
        pitcher_embed_size: Dimension of the embedding vector for each pitcher.
        density_size: Dimension of the pitch density vector for each pitcher.
        density_hidden_nodes: List of ints; each element is the number of nodes in the ith
            hidden layer on the pitch density inputs before it's concatenated with the rest
            of the inputs.
        graph: Tensorflow graph object with the model graph.
        saver: A TensorFlow saver object for saving model variables.
        session: Tensorflow session object.
        node_names: List with names of all nodes in the graph.
        fit_log: Dictionary with names "batch_number" (list of batch numbers after which
            validation was scored) and "validation_score" (list of validation scores aligned
            with batch_number).
        fit_time: Number of seconds taken to fit the model.
    """
    num_numeric_inputs = 47
    num_outcomes = 5

    def __init__(self, batch_size=32, learning_rate=0.1, dropout_rate=0.5, hidden_nodes=[96],
                 num_batters=None, batter_embed_size=16, num_pitchers=None, pitcher_embed_size=16,
                 density_size=None, density_hidden_nodes=None):
        """Default constructor."""
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.dropout_rate = dropout_rate
        self.hidden_nodes = hidden_nodes
        self.num_batters = num_batters
        self.batter_embed_size = batter_embed_size
        self.num_pitchers = num_pitchers
        self.pitcher_embed_size = pitcher_embed_size
        self.density_size = density_size
        self.density_hidden_nodes = density_hidden_nodes

        self.graph = tf.Graph()
        with self.graph.as_default():
            self._build_graph()
            self.session = tf.Session(graph=self.graph)
            self.saver = tf.train.Saver()
            self.session.run(tf.global_variables_initializer())
        self.node_names = [node.name + ":0" for node in self.graph.as_graph_def().node]
        self.fit_log = {"batch_number": [],
                        "validation_score": []}
        self.fit_time = None

    def _build_graph(self):
        data, outcomes = self._build_inputs()
        self.dropout = tf.placeholder(tf.float32, None, name="dropout")
        hidden_outputs = [data]
        for num_nodes in self.hidden_nodes:
            hidden_outputs.append(self._build_hidden_layer(hidden_outputs[-1], num_nodes))
        self.logit_output = self._build_output_layer(hidden_outputs[-1])
        self.loss = self._build_loss(self.logit_output, outcomes)
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
        if self.density_size:
            inputs.append(self._build_density_input())
        final_input = tf.concat(inputs, 1)
        return final_input, pitch_outcomes

    def _build_batter_input(self):
        batter_ids = tf.placeholder(tf.int32, shape=[self.batch_size], name="batter_ids")
        batter_embedding = tf.Variable(tf.random_normal([self.num_batters,
                                                         self.batter_embed_size], stddev=0.1))
        batter_embedded = tf.nn.embedding_lookup(batter_embedding, batter_ids)
        return batter_embedded

    def _build_pitcher_input(self):
        pitcher_ids = tf.placeholder(tf.int32, shape=[self.batch_size], name="pitcher_ids")
        pitcher_embedding = tf.Variable(tf.random_normal([self.num_pitchers,
                                                          self.pitcher_embed_size], stddev=0.1))
        pitcher_embedded = tf.nn.embedding_lookup(pitcher_embedding, pitcher_ids)
        return pitcher_embedded

    def _build_density_input(self):
        density = tf.placeholder(tf.float32, shape=[self.batch_size] + self.density_size,
                                 name="pitch_density")
        if self.density_hidden_nodes:
            density_outputs = [density]
            for num_nodes in self.density_hidden_nodes:
                density_outputs.append(self._build_hidden_layer(density_outputs[-1], num_nodes))
            return density_outputs[-1]
        else:
            return density

    def _build_hidden_layer(self, hidden_input, hidden_nodes):
        input_dim = hidden_input.get_shape().as_list()
        hidden_weight = tf.Variable(tf.random_normal([input_dim[1], hidden_nodes], stddev=0.05))
        hidden_bias = tf.Variable(tf.random_normal([hidden_nodes], stddev=0.1))
        hidden_logits = tf.matmul(hidden_input, hidden_weight) + hidden_bias
        hidden_scores = tf.nn.sigmoid(hidden_logits)
        hidden_output = tf.nn.dropout(hidden_scores, self.dropout)
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
        """Train the model.

        Inputs:
            train_data: PitchData object with training data.
            validation_date: PitchData object with validation data.
            training_steps: Number of batches to train.
            print_every: How often to calculate and show validation results.
        """
        start_time = datetime.datetime.now()
        current_step = 0
        while current_step < training_steps:
            self._train_steps(train_data, print_every)
            current_step += print_every
            current_score = self.score(validation_data)
            print("{:>7} - {:0.4f}".format(current_step, round(current_score, 4)))
            self.fit_log["batch_number"].append(current_step)
            self.fit_log["validation_score"].append(current_score)

        end_time = datetime.datetime.now()
        self.fit_time = (end_time - start_time).total_seconds()

    def _train_steps(self, train_data, num_steps):
        for _ in range(num_steps):
            input_dict = self._filter_input_dict(train_data.get_batch(self.batch_size))
            input_dict["dropout:0"] = self.dropout_rate
            _, loss = self.session.run([self.optimizer, self.loss], feed_dict=input_dict)

    def score(self, data):
        """Score a data set through the model.

        Inputs:
            data: PitchData object with data to score.
        Returns:
            The model's perplexity w.r.t. data.
        """
        scores = []
        while not data.has_reached_end():
            input_dict = self._filter_input_dict(data.get_batch(self.batch_size))
            input_dict["dropout:0"] = 1.0
            loss = self.session.run([self.loss], feed_dict=input_dict)
            scores.append(loss)
        return math.exp(np.mean(scores))

    def predict(self, data):
        """Predict outcomes for a data set.

        Inputs:
            data: PitchData object with data to predict.
        Returns:
            A NumPy array with dimensions of [number of observations in data] by 5. Each row
            is an observation, and each column is the logit of a prediction for a particular
            output.
        """
        predictions = []
        while not data.has_reached_end():
            input_dict = self._filter_input_dict(data.get_batch(self.batch_size))
            input_dict["dropout:0"] = 1.0
            pred_logits = self.session.run([self.logit_output], feed_dict=input_dict)
            pred_unnormed = np.exp(np.reshape(pred_logits, [-1, self.num_outcomes]))
            prediction = pred_unnormed / np.sum(pred_unnormed, axis=1, keepdims=True)
            predictions.append(prediction)
        return functools.reduce(lambda x, y: np.append(x, y, axis=0), predictions)

    def save(self, filename):
        """Save the values of all model variables to a file."""
        # TODO: Create folder if it doesn't exist
        self.saver.save(self.session, filename)

    def restore(self, filename):
        """Restore the values of all model variables from a file."""
        self.saver.restore(self.session, filename)

    def _filter_input_dict(self, input_dict):
        for k in input_dict.keys():
            if k not in self.node_names:
                del input_dict[k]
        return input_dict
