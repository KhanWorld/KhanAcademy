import sharded_counter

# Keep a global count of registered users

def get_count():
    '''Get the number of registered users'''
    return sharded_counter.get_count('user_counter')

def add(n):
    '''Add n to the counter (n < 0 is valid)'''
    sharded_counter.add('user_counter', n)

def change_number_of_shards(num):
    '''Change the number of shards to num'''
    sharded_counter.change_number_of_shards('user_counter', num)
