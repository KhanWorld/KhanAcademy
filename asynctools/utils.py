""" utils """
from itertools import chain, islice

class Chunker(list):
    """ Take arbitary lists,
        provides
         - a batch chunk iterator for processing
         - ressemble results according to original input list sizes

        Chunker([[key1,key2], [key3], [], [key4,key5,key6]])

            ichain():
            return  iter([key1, key2, key3, key4, key5, key6])

            ichunk(size=2):
            return iter([[key1, key2], [key3, key4], [key5, key6]])

            isplit([[result1,result2], [result3, result4], [result5,result6]]):
            return iter([[result1,result2], [result3], [], [result4,result5,result6]])

            iprocess(func, size=2):
            chunk -> func -> split

            chunk(size=2):
            returns list instead of an iterator

            split(result):
            returns list instead of an iterator

            process(func, size=2):
            chunk -> func -> split
    """


    def __init__(self, iters=None):
        """Copy in iters as lists"""
        super(Chunker, self).__init__(self)
        if iters:
            self.extend( [ i if type(i) is list else list(i) for i in iters ] )

    def append(self, iter):
        """append ensuring a list"""
        super(Chunker, self).append(iter if type(iter) is list else list(iter))

    def insert(self, index, iter):
        """insert ensuring a list"""
        super(Chunker, self).insert(index, iter if type(iter) is list else list(iter))

    def ichain(self):
        """ return self chained as one iterator """
        return chain(*self)

    def ichunk(self, size=1):
        """ return batch chunks of self as an iterator"""
        items = self.ichain()
        return ([item]+list(islice(items, size-1)) for item in items)

    def isplit(self, chunks):
        """ rechunk batch chunks to be the same as self via an iterator"""
        items = chain(*chunks)
        groups = iter(self)
        return (list(islice(items, len(group))) for group in groups)

    def chunk(self, size=1):
        """ return batch chunks of self """
        return list(self.ichunk(size=size))

    def split(self, chunks):
        """ rechunk batch chunks to be the same as self via an iterator"""
        return list(self.isplit(chunks))

    def iprocess(self, func, size=1):
        """return iterator after batch chunking over func"""
        return self.isplit(func(item) for item in self.ichunk(size=size))

    def process(self, func, size=1):
        """return result after batch chunking over func"""
        return list(self.iprocess(func, size=size))

