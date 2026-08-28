#!/usr/bin/env python3

from math import e
import sys
from sys import stdin, stdout, stderr, exit
from os import SEEK_SET, SEEK_CUR, SEEK_END
from errno import EPIPE
from struct import pack, unpack

__all__ = ('decompress', 'decompress_file', 'decompress_bytes',
           'decompress_overlay', 'DecompressionError')

class DecompressionError(ValueError):
    pass

def bits(byte):
    return ((byte >> 7) & 1,
            (byte >> 6) & 1,
            (byte >> 5) & 1,
            (byte >> 4) & 1,
            (byte >> 3) & 1,
            (byte >> 2) & 1,
            (byte >> 1) & 1,
            (byte) & 1)

def decompress_raw_lzss10(indata, decompressed_size, _overlay=False):
    """Decompress LZSS-compressed bytes. Returns a bytearray."""
    data = bytearray()

    it = iter(indata)

    if _overlay:
        disp_extra = 3
    else:
        disp_extra = 1

    def writebyte(b):
        data.append(b)
    def readbyte():
        return next(it)
    def readshort():
        # big-endian
        a = next(it)
        b = next(it)
        return (a << 8) | b
    def copybyte():
        data.append(next(it))

    while len(data) < decompressed_size:
        b = readbyte()
        flags = bits(b)
        for flag in flags:
            if flag == 0:
                copybyte()
            elif flag == 1:
                sh = readshort()
                count = (sh >> 0xc) + 3
                disp = (sh & 0xfff) + disp_extra

                for _ in range(count):
                    writebyte(data[-disp])
            else:
                raise ValueError(flag)

            if decompressed_size <= len(data):
                break

    if len(data) != decompressed_size:
        raise DecompressionError("decompressed size does not match the expected size")

    return data

def decompress_raw_lzss11(indata, decompressed_size):
    """Decompress LZSS-compressed bytes. Returns a bytearray."""
    data = bytearray()

    it = iter(indata)

    def writebyte(b):
        data.append(b)
    def readbyte():
        return next(it)
    def copybyte():
        data.append(next(it))

    while len(data) < decompressed_size:
        b = readbyte()
        flags = bits(b)
        for flag in flags:
            if flag == 0:
                copybyte()
            elif flag == 1:
                b = readbyte()
                indicator = b >> 4

                if indicator == 0:
                    # 8 bit count, 12 bit disp
                    # indicator is 0, don't need to mask b
                    count = (b << 4)
                    b = readbyte()
                    count += b >> 4
                    count += 0x11
                elif indicator == 1:
                    # 16 bit count, 12 bit disp
                    count = ((b & 0xf) << 12) + (readbyte() << 4)
                    b = readbyte()
                    count += b >> 4
                    count += 0x111
                else:
                    # indicator is count (4 bits), 12 bit disp
                    count = indicator
                    count += 1

                disp = ((b & 0xf) << 8) + readbyte()
                disp += 1

                try:
                    for _ in range(count):
                        writebyte(data[-disp])
                except IndexError:
                    raise Exception(count, disp, len(data), sum(1 for x in it) )
            else:
                raise ValueError(flag)

            if decompressed_size <= len(data):
                break

    if len(data) != decompressed_size:
        raise DecompressionError("decompressed size does not match the expected size")

    return data


def decompress_overlay(f, out):
    # the compression header is at the end of the file
    f.seek(-8, SEEK_END)
    header = f.read(8)

    # decompression goes backwards.
    # end < here < start

    # end_delta == here - decompression end address
    # start_delta == decompression start address - here
    end_delta, start_delta = unpack("<LL", header)

    filelen = f.tell()

    padding = end_delta >> 0x18
    end_delta &= 0xFFFFFF
    decompressed_size = start_delta + end_delta

    f.seek(-end_delta, SEEK_END)

    data = bytearray()
    data.extend(f.read(end_delta - padding))
    data.reverse()

    #stdout.write(data.tostring())

    uncompressed_data = decompress_raw_lzss10(data, decompressed_size,
                                              _overlay=True)
    uncompressed_data.reverse()

    # first we write up to the portion of the file which was "overwritten" by
    # the decompressed data, then the decompressed data itself.
    # i wonder if it's possible for decompression to overtake the compressed
    # data, so that the decompression code is reading its own output...
    f.seek(0, SEEK_SET)
    out.write(f.read(filelen - end_delta))
    out.write(uncompressed_data)

def decompress(obj):
    """Decompress LZSS-compressed bytes or a file-like object.

    Shells out to decompress_file() or decompress_bytes() depending on
    whether or not the passed-in object has a 'read' attribute or not.

    Returns a bytearray."""
    if hasattr(obj, 'read'):
        return decompress_file(obj)
    else:
        return decompress_bytes(obj)

def decompress_bytes(data):
    """Decompress LZSS-compressed bytes. Returns a bytearray."""
    header = data[:4]
    if header[0] == 0x10:
        decompress_raw = decompress_raw_lzss10
    elif header[0] == 0x11:
        decompress_raw = decompress_raw_lzss11
    else:
        raise DecompressionError("not as lzss-compressed file")

    decompressed_size, = unpack("<L", header[1:] + b'\x00')

    data = data[4:]
    return decompress_raw(data, decompressed_size)

def decompress_file(f):
    """Decompress an LZSS-compressed file. Returns a bytearray.

    This isn't any more efficient than decompress_bytes, as it reads
    the entire file into memory. It is offered as a convenience.
    """
    header = f.read(4)
    if header[0] == 0x10:
        decompress_raw = decompress_raw_lzss10
    elif header[0] == 0x11:
        decompress_raw = decompress_raw_lzss11
    else:
        #raise DecompressionError(f"{filename} not lzss-compressed file")
        return([0x0], 0)

    decompressed_size, = unpack("<L", header[1:] + b'\x00')

    data = f.read()
    return decompress_raw(data, decompressed_size)

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    if '--overlay' in args:
        args.remove('--overlay')
        overlay = True
    else:
        overlay = False

    if len(args) < 1 or args[0] == '-':
        if overlay:
            print("Can't decompress overlays from stdin", file=stderr)
            return 2

        if hasattr(stdin, 'buffer'):
            f = stdin.buffer
        else:
            f = stdin
    else:
        try:
            f = open(args[0], "rb")
        except IOError as e:
            print(e, file=stderr)
            return 2

    stdout = sys.stdout
    if hasattr(stdout, 'buffer'):
        # grab the underlying binary stream
        stdout = stdout.buffer

    try:
        if overlay:
            decompress_overlay(f, stdout)
        else:
            stdout.write(decompress_file(f))
    except IOError as e:
        if e.errno == EPIPE:
            # don't complain about a broken pipe
            pass
        else:
            raise
    except (DecompressionError,) as e:
        print(e, file=stderr)
        return 1

    return 0

def compress_raw_lzss11(indata):
    """
    Compress an uncompressed byte sequence using Nintendo LZ11.
    """
    data = bytes(indata)
    size = len(data)

    if size == 0:
        return bytearray()

    # LZ11 limits.
    MAX_DISP = 4096
    MAX_LENGTH = 0x10110       # 65808
    MIN_LENGTH = 3

    # Number of dictionary entries examined when looking for a match.
    # Increasing this can improve compression at the cost of speed.
    MAX_CANDIDATES = 128

    output = [0x11]

    for byte_value in size.to_bytes(3, 'little'):
        output.append(byte_value)

    # Hash-chain dictionary.
    #
    # head[key] = most recent position containing the 3-byte key
    # prev[pos] = previous position containing the same key
    head = {}
    prev = [-1] * size

    def add_position(pos):
        """Add a newly available position to the LZ dictionary."""
        if pos + 3 > size:
            return

        key = data[pos:pos + 3]
        prev[pos] = head.get(key, -1)
        head[key] = pos

    def find_match(pos):
        """
        Find the longest previous match at data[pos:].

        Returns:
            (length, displacement)

        or:
            (0, 0) if no match of at least 3 bytes exists.
        """
        if pos + 3 > size:
            return 0, 0

        key = data[pos:pos + 3]
        candidate = head.get(key, -1)

        if candidate < 0:
            return 0, 0

        minimum_position = max(0, pos - MAX_DISP)
        maximum_length = min(MAX_LENGTH, size - pos)

        best_length = 0
        best_disp = 0
        candidates_checked = 0

        while (
            candidate >= minimum_position
            and candidate >= 0
            and candidates_checked < MAX_CANDIDATES
        ):
            length = 3

            # This deliberately allows overlapping matches.
            #
            # For example, if the source is:
            #
            #     ABCABCABCABC...
            #
            # a match can reference bytes that are themselves being
            # generated by the match.
            while (
                length < maximum_length
                and data[candidate + length] == data[pos + length]
            ):
                length += 1

            if length > best_length:
                best_length = length
                best_disp = pos - candidate

                if length == maximum_length:
                    break

            candidate = prev[candidate]
            candidates_checked += 1

        return best_length, best_disp

    pos = 0

    while pos < size:
        flags = 0
        tokens = []

        # One LZ11 flag byte controls up to 8 tokens.
        for bit in range(8):
            if pos >= size:
                break

            length, disp = find_match(pos)

            if length >= MIN_LENGTH:
                length = min(length, MAX_LENGTH)

                # LZ11 stores displacement minus one.
                d = disp - 1

                if length <= 16:
                    #
                    # Format:
                    #
                    #   b0 = CCCC DDDD
                    #   b1 = DDDDDDDD
                    #
                    # CCCC = length - 1
                    # DDDD... = displacement - 1
                    #
                    indicator = length - 1

                    token = bytes((
                        (indicator << 4) | (d >> 8),
                        d & 0xFF,
                    ))

                elif length <= 0x110:
                    #
                    # Format:
                    #
                    #   b0 = 0000 CCCC
                    #   b1 = CCCC DDDD
                    #   b2 = DDDDDDDD
                    #
                    # Encoded length = actual length - 0x11
                    #
                    encoded_length = length - 0x11

                    token = bytes((
                        (encoded_length >> 4) & 0x0F,
                        ((encoded_length & 0x0F) << 4) | (d >> 8),
                        d & 0xFF,
                    ))

                else:
                    #
                    # Format:
                    #
                    #   b0 = 0001 CCCC
                    #   b1 = CCCCCCCC
                    #   b2 = CCCC DDDD
                    #   b3 = DDDDDDDD
                    #
                    # Encoded length = actual length - 0x111
                    #
                    encoded_length = length - 0x111

                    token = bytes((
                        0x10 | ((encoded_length >> 12) & 0x0F),
                        (encoded_length >> 4) & 0xFF,
                        ((encoded_length & 0x0F) << 4) | (d >> 8),
                        d & 0xFF,
                    ))

                # This is a compressed token, so set the corresponding flag.
                flags |= 1 << (7 - bit)
                tokens.append(token)

                old_pos = pos
                pos += length

                # Every byte which has now been produced can be used as a
                # future dictionary source.
                for i in range(old_pos, pos):
                    add_position(i)

            else:
                # Literal byte.
                tokens.append(bytes((data[pos],)))

                old_pos = pos
                pos += 1
                add_position(old_pos)

        output.append(flags)

        for token in tokens:
            output.extend(token)

    return output

if __name__ == '__main__':
    exit(main())
