"""
Parameters (weights) for logistic regression.

Training specs
--------------
Dataset: last 1 million problems logs since Sept. 2
Using full history: Yes
Predicting on: All problems done except first
"""

INTERCEPT = -0.6384147
EWMA_3 = 0.9595278
EWMA_10 = 1.3383701
CURRENT_STREAK = 0.0070444
LOG_NUM_DONE = 0.4862635
LOG_NUM_MISSED = -0.7135976
PERCENT_CORRECT = 0.6336906
