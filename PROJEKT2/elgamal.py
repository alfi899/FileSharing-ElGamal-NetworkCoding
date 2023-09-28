import random

"""
16 bit ->  p = 53147 q = 26573
64 bit ->  p = 17268743455956267047  q = 8634371727978133523
128 bit -> p 
"""

class Gamal:
    def __init__(self):
        self.a = random.randint(2, 10)  # private key
        self.p =  53147 #self.generate_prime_number(64)
        self.q = 26573
        self.g = 3736 #random.randint(2, self.p) # generator known for all
        self.private_key = 17# self.gen_key(self.p) # private key for receiver
        self.public_key = self.power(self.g, self.private_key, self.p) # public key


    def is_prime(self, n, k=128):
        """ Test if a number is prime
            Args:
                n (int): the number to test
                k (int): the number of tests to do
            return True if n is prime

            Thanks to https://medium.com/@ntnprdhmm/how-to-generate-big-prime-numbers-miller-rabin-49e6e6af32fb
        """
        # Test if n is not even
        # But care, 2 is prime!
        if n == 2 or n==3:
            return True
        if n <= 1 or n % 2 == 0:
            return False
        # find r and s
        s = 0
        r = n -1 
        while r & 1 == 0:
            s += 1 
            r//= 2 
        # do k tests
        for _ in range(k):
            a = random.randrange(2, n-1)
            x = pow(a,r,n)
            if x != 1 and x != n -1:
                j = 1
                while j < s and x != n-1:
                    x = pow(x,2,n)
                    if x == 1:
                        return False 
                    j += 1
                if x != n -1:
                    return False
        return True

    def generate_prime_condidate(self, length):
        """ Generate an odd integer randomly
            Args:
                length (int): the lenght of the number to generate, in bits
            return an integer
        """
        p = random.getrandbits(length)
        p |= (1 << length - 1) | 1
        return p 

    def generate_prime_number(self, length=1024):
        """ Generate a prime
            Args:
                length (int): length of the prime to generate, in bits
            return a prime
        """
        p = 4 
        # keep generating while the primality test fail
        while not self.is_prime(p, 128):
            p = self.generate_prime_condidate(length)
        return p

    def gcd(self, a, b):
        if a < b:
            return self.gcd(b, a)
        elif a % b == 0:
            return b;
        else:
            return self.gcd(b, a % b)
        
    def gen_key(self, q):
        key = random.randint(2, q) #random.randint(pow(10,20), q)
        while self.gcd(q, key) != 1:
            key = random.randint(2, q) #random.randint(pow(10,20), q)
        return key

    def power(self, a, b, c):
        x = 1
        y = a
        while b > 0:
            if b % 2 != 0:
                x = (x * y) % c;
            y = (y * y) % c
            b = int(b / 2)
        return x % c
    
 
    def encryption(self, message):
        c2 = []
        r = random.randint(2, self.p - 1) 
        s = self.power(self.public_key, r, self.p)
        c1 = self.power(self.g, r, self.p)

        for i in range(0, len(message)):
            c2.append(message[i])
        for i in range(0, len(c2)):
            c2[i] = (s * c2[i]) % self.p

        return c1, c2
    
    def decryption(self, c1, c2, key):
        dr_msg = []
        for i in range(0, len(c2)):
            x = (c2[i] * pow(c1, -1*key, self.p)) % self.p
            dr_msg.append(x)
        return dr_msg