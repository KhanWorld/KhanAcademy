import logging
import itertools
import math

def exponential_fit(X, Y):
    # See http://mathworld.wolfram.com/LeastSquaresFittingExponential.html
    # TODO(david): This just uses the simpler fit given by equations (3) and (4) of
    #     above link. Try equations (9) and (10).
    # TODO(david): Use numpy when supported

    def sqr(x):
        return x * x

    n = len(X)
    sum_x = sum(X)
    sum_log_y = sum(itertools.imap(math.log, Y))
    sum_x_log_y = sum(itertools.imap(lambda x, y: x * math.log(y), X, Y))
    sum_x_sqr = sum(itertools.imap(sqr, X))

    a_num = sum_log_y * sum_x_sqr - sum_x * sum_x_log_y
    b_num = n * sum_x_log_y - sum_x * sum_log_y
    den = n * sum_x_sqr - sqr(sum_x)

    a = float(a_num) / den
    b = float(b_num) / den

    return math.exp(a), b

class InvFnExponentialNormalizer(object):
    """
    This is basically a function that takes an accuracy prediction (probability
    of next problem correct) and attempts to "evenly" distribute it in [0, 1]
    such that progress bar appears to fill up linearly.

    The current algorithm is as follows:
    Let
        f(n) = probabilty of next problem correct after doing n problems,
        all of which are correct.
    Let
        g(x) = f^(-1)(x)
    that is, the inverse function of f. Since f is discrete but we want g to be
    continuous, unknown values in the domain of g will be approximated by using
    an exponential curve to fit the known values of g. Intuitively, g(x) is a
    function that takes your accuracy and returns how many problems correct in
    a row it would've taken to get to that, as a real number. Thus, our
    progress display function is just
        h(x) = g(x) / g(consts.PROFICIENCY_ACCURACY_THRESHOLD)
    clamped between [0, 1].

    The rationale behind this is that if you don't get any problems wrong, your
    progress bar will increment by about the same amount each time and be full
    right when you're proficient (i.e. reach the required accuracy threshold).

    (Sorry if the explanation is not very clear... best to draw a graph of f(n)
    and g(x) to see for yourself.)

    This is a class because of static initialization of state.
    """

    def __init__(self, accuracy_model, proficiency_threshold):
        X, Y = [], []
        self.proficiency_threshold = proficiency_threshold

        for i in itertools.count(1):
            accuracy_model.update(correct=True)
            probability = accuracy_model.predict()

            X.append(probability)
            Y.append(i)

            if probability >= proficiency_threshold:
                break

        self.A, self.B = exponential_fit(X, Y)
        # normalize the function output so that it outputs 1.0 at the proficency threshold
        self.A /= self.exponential_estimate(proficiency_threshold)

    def exponential_estimate(self, x):
        return self.A * math.exp(self.B * x)

    def normalize(self, p_val):
        # TODO(david): Use numpy clip
        def clamp(value, minval, maxval):
            return sorted((minval, value, maxval))[1]

        return clamp(self.exponential_estimate(p_val), 0.0, 1.0)
