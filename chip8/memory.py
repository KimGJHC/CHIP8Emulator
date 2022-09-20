class Memory(object):

    def __init__(self):
        """Allocates 4KB (4096 bytes) for program memory."""
        self._mem = bytearray(0x1000)

    def store_byte(self, addr, data):
        """Stores 1 byte of data at the given address."""
        if addr < 0 or addr >= len(self._mem):
            raise ValueError
        self._mem[addr] = data & 0xff # 11111111
        return True

    def fetch_byte(self, addr):
        """Fetches 1 byte of data from the given address."""
        if addr < 0 or addr >= len(self._mem):
            raise ValueError
        return self._mem[addr]

    def store_word(self, addr, data):
        """Stores word (2 bytes) of data at the given address."""
        if addr < 0 or addr + 1 >= len(self._mem):
            raise ValueError
        self._mem[addr] = (data >> 8) & 0xff
        self._mem[addr + 1] = data & 0xff
        return True

    def fetch_word(self, addr):
        """Fetches word (2 bytes) of data from the given address."""
        if addr < 0 or addr + 1 >= len(self._mem):
            raise ValueError
        return (self._mem[addr] << 8 | self._mem[addr + 1])

    def store_many(self, addr, data):
        """Stores many bytes of data at the given address."""
        if addr < 0 or addr + len(data) - 1 >= len(self._mem):
            raise ValueError
        for i, byte in enumerate(data):
            self._mem[addr + i] = byte & 0xff
        return True

    def fetch_many(self, addr, length):
        """Fetched many bytes of data from the given address."""
        if addr < 0 or addr + length - 1 >= len(self._mem):
            raise ValueError
        return self._mem[addr:addr + length]

