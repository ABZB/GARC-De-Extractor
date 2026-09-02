import os
from sys import byteorder
from tkinter.filedialog import askdirectory, askopenfilename, askopenfilenames, asksaveasfilename
from shutil import copy2
import csv
from Rename import *
from lzss3 import *
from lzss3 import compress_raw_lzss11
from lzss3 import decompress_raw_lzss11
from tkfilebrowser import askopendirnames


def flibi(bytedata):
    return(int.from_bytes(bytedata, "little"))

def decompress_file(filepath_set, altpath = ''):
    for filepath in filepath_set:
        with open(filepath, 'r+b') as source_file:
            source_data = source_file.read()

            if(source_data[0] != 0x11):
                if(altpath == ''):
                    print(f'{filepath} is not compressed!\n')
                    return
                else:
                    if(not os.path.isdir(os.path.abspath(os.path.join(altpath, os.pardir)))):
                        os.mkdir(os.path.abspath(os.path.join(altpath, os.pardir)))
                    with open(altpath, 'w+b') as g:
                        g.write(bytes(source_data))
                        g.truncate()
            else:
                source_file.seek(0)
                print(f'\tDecompressing {filepath}\n')

                if(altpath == ''):
                    source_file.write(bytes(decompress_bytes(source_data)))
                    source_file.truncate()
                else:
                    if(not os.path.isdir(os.path.abspath(os.path.join(altpath, os.pardir)))):
                        os.mkdir(os.path.abspath(os.path.join(altpath, os.pardir)))
                    with open(altpath, 'w+b') as g:
                        g.write(bytes(decompress_bytes(source_data)))
                        g.truncate()

def compress_file(filepath_set, altpath = ''):
    for filepath in filepath_set:
        with open(filepath, 'r+b') as source_file:
            source_data = source_file.read()

            if(source_data[0] == 0x11):
                if(altpath == ''):
                    print(f'{filepath} is already compressed!\n')
                    return
                else:
                    if(not os.path.isdir(os.path.abspath(os.path.join(altpath, os.pardir)))):
                        os.mkdir(os.path.abspath(os.path.join(altpath, os.pardir)))
                    with open(altpath, 'w+b') as g:
                        g.write(bytes(source_data))
                        g.truncate()
            else:
                source_file.seek(0)
                print(f'\tCompressing {filepath}\n')
                if(altpath == ''):
                    source_file.write(bytes(compress_raw_lzss11(source_data)))
                    source_file.truncate()
                else:
                    if(not os.path.isdir(os.path.abspath(os.path.join(altpath, os.pardir)))):
                        os.mkdir(os.path.abspath(os.path.join(altpath, os.pardir)))
                    with open(altpath, 'w+b') as g:
                        g.write(bytes(compress_raw_lzss11(source_data)))


def decompress_folder(folder_path_set):
    for folder_path in folder_path_set:
        output_folder = os.path.join(os.path.dirname(folder_path), os.path.basename(folder_path) + '_decompressed')
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        for filename in os.listdir(folder_path):
            decompress_file(os.path.join(folder_path, filename), os.path.join(output_folder, filename))

        print(f'\tDecompressed {folder_path} to {output_folder}\n')
        return(output_folder)

def compress_folder(folder_path_set):
    for folder_path in folder_path_set:
        file_count = len([name for name in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, name))])

        if(file_count > 9999):
            print('Assuming compressing Model Garc, not compressing file 00000.bin')

        output_folder = os.path.join(os.path.dirname(folder_path), os.path.basename(folder_path) + '_compressed')
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        for filename in os.listdir(folder_path):
            if(filename != '00000.bin'):
                compress_file(os.path.join(folder_path, filename), os.path.join(output_folder, filename))

        print(f'\tCompressed {folder_path} to {output_folder}\n')
        return(output_folder)

def extract_garc(filepath_set):
    for filepath in filepath_set:
        while True:
            write_dir =  filepath + '_extracted_GARC'
            if(input(f'Use {write_dir} as output folder? Y/N\n').lower() == 'y'):
                if(not os.path.isdir(write_dir)):
                    os.makedirs(write_dir)
            else:
                write_dir = askdirectory(title = f'Select folder to write extracted files from {filepath} to')


            if(not os.path.exists(write_dir)):
                os.makedirs(write_dir)


            #empty is false only if directory has stuff in it
            empty = True
            for _ in os.scandir(write_dir):
                empty = False
                break

            if(empty):
                break
            else:
                if(input('Selected directory is non-empty, proceeding will first delete all current files (but not folders) inside of it, proceed? y/n\n').lower() == 'y'):

                    for filename in os.listdir(write_dir):
                        temp = os.path.join(write_dir, filename)
                        if(not(os.path.isdir(temp))):
                            os.remove(temp)
                    break
                else:
                    print('Please select a different directory')


        while True:
            decompress_now = False
            break


            decompress_now = input('Decompress as we extract? y/n\n').lower()

            if(decompress_now == 'y'):
                decompress_now = True
                break
            elif(decompress_now == 'n'):
                decompress_now = False
                break
            else:
                print(f'{decompress_now} not understood as a valid answer')


        with open(filepath, 'r+b') as source_file:
            bindata = source_file.read()

        FAT0_offset = 0x24
        FATB_offset = FAT0_offset + flibi(bindata[FAT0_offset + 0x4:FAT0_offset + 0x8])
        file_count = flibi(bindata[FAT0_offset + 0x8:FAT0_offset + 0xA])
        data_absolute_offset = flibi(bindata[0x10:0x14])

        #0xC is start of the actual file location/length data.
        FATB_offset += 0xC
    
        fillz = 5 if file_count >= 5000 else 4
        for file_number in range(file_count):

            with open(os.path.join(write_dir, str(file_number).zfill(fillz) + '.bin'), 'w+b') as f:

                #pointer to start of next file
                data_offset = data_absolute_offset + flibi(bindata[FATB_offset + 0x4:FATB_offset + 0x8])

                #get length of current file
                file_length = flibi(bindata[FATB_offset + 0xC:FATB_offset + 0x10])

                #write data to next bin file
                f.write(bytes(decompress_bytes(bindata[data_offset:data_offset + file_length])) if (decompress_now and bindata[data_offset] == 0x11) else bytes(bindata[data_offset:data_offset + file_length]))

                #the offset end is different than start + length because length is padded to multiple of 4.

            FATB_offset += 0x10
        print(f'\Extracted the GARC {filepath} to {write_dir}\n')



        if(input('Decompress now? y/n\n').lower() == 'y'):
            for file in os.listdir(write_dir):
                decompress_file(file)



def write_garc(file, offset, value):

    
    file.seek(offset)
    file.write(bytes(value))

def build_garc(folder_path_set):

    for folder_path in folder_path_set:
        write_file = asksaveasfilename(title = f'Choose GARC to build from {folder_path}')

        print('Confirming file names are consistent')
        rename_handler(folder_path, 'b')



        file_count = len([name for name in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, name))])

        print('Begin Build')
        with open(write_file, 'w+b') as target:

            temp = [0x0]*0x1C
            #magic GARC
            write_garc(target, 0x0, [0x43, 0x52, 0x41, 0x47])

            #Endian
            write_garc(target, 0x8, [0xFF, 0xFE, 0x00, 0x00])

            #SM/USUM
            write_garc(target, 0x4, (0x24).to_bytes(4, byteorder = 'little'))
            write_garc(target, 0xB, (0x06).to_bytes(1, byteorder = 'little'))
            FAT0_offset = 0x24

            #section count
            write_garc(target, 0xC, (0x4).to_bytes(1, byteorder = 'little'))

            #FAT0 Header allocation
            end_FAT_zero_header = (0xC + 4*file_count)
    
            #Magic FAT0
            write_garc(target, FAT0_offset, [0x4F, 0x54, 0x41, 0x46])
    
            #FAT0 length
            write_garc(target, FAT0_offset + 0x4, (file_count*4 + 0xC).to_bytes(4, byteorder = 'little'))

            #file count
            write_garc(target, FAT0_offset + 0x8, (file_count).to_bytes(2, byteorder = 'little'))

            #padding
            write_garc(target, FAT0_offset + 0xA, [0xFF, 0xFF])


            #write FAT0 thing
            pointer = FAT0_offset + 0xC
            for x in range(file_count):
                write_garc(target, pointer, (x * 0x10).to_bytes(4, byteorder = 'little'))
                pointer += 0x4


            #allocate FATB, 0xC for header, then 0x10 per file
            #magic FATB
            write_garc(target, pointer, [0x42, 0x54, 0x41, 0x46])

            pointer +=4

            #BFAT length
            write_garc(target, pointer, (file_count*0x10 + 0xC).to_bytes(4, byteorder = 'little'))

            pointer +=4

            #BFAT file count
            write_garc(target, pointer, (file_count).to_bytes(2, byteorder = 'little'))

            pointer += 4

            #pointer now at start of FATB blocks, there are 0x10*file_count bytes in it

            fimb_pointer = pointer + file_count*0x10
        



            #magic FIMB
            write_garc(target, fimb_pointer, [0x42, 0x4D, 0x49, 0x46])
    
            fimb_pointer  += 4

            #FIMB header length (3 high bytes are zero)
            write_garc(target, fimb_pointer, (0x0C).to_bytes(4, byteorder = 'little'))


            #need to update this with final offset below
            fimb_pointer  += 4


            data_pointer = fimb_pointer + 4


            write_garc(target, 0x10, (data_pointer).to_bytes(4, byteorder = 'little'))
            print('Header initialized')
            offset = 0
            biggest_size = 0
            biggest_size_padding = 0
            for countcount, filename in enumerate(os.listdir(folder_path)):

                if(countcount % (file_count//20) == 0):
                    print(f'{countcount*100//file_count}%')

                #don't do anything wih subfolders
                if(os.path.isdir(filename)):
                    continue

                with open(os.path.join(folder_path, filename), 'r+b') as current_source:
                
                    #padding
                    write_garc(target, pointer, [0x01, 0x00, 0x00, 0x00])

                    #offset start
                    write_garc(target, pointer + 4, (offset).to_bytes(4, byteorder = 'little'))

                    current_source.seek(0, 2)


                    length = current_source.tell()
        
        
                    biggest_size = max(length, biggest_size)
                    padding = 4 - (length % 4) if (length % 4) != 0 else 0
                    biggest_size_padding = max(length + padding, biggest_size_padding)
                    offset += length + padding

                    #offset end. When there is padding to z bytes, those extra bytes are filled with 0xFF, are NOT counted in the length, but ARE counted in the end-address
                    write_garc(target, pointer + 8, (offset).to_bytes(4, byteorder = 'little'))

                    #length
                    write_garc(target, pointer + 0xC, (length).to_bytes(4, byteorder = 'little'))

                    current_source.seek(0)
                    write_garc(target, data_pointer, current_source.read())



                    if(padding != 0):
                        temp.extend([0xFF]*padding)
                        write_garc(target, data_pointer + length, [0xFF]*padding)

                    data_pointer += length + padding

                    pointer += 0x10

            #write total length of files
            write_garc(target, fimb_pointer, (offset).to_bytes(4, byteorder = 'little'))
    
            #in GARC header, need to write file length, and largest file size (plus padded max and padding in gen 7)

            #only write largest file size at FAT0_offset - 4
           # if(poke_edit_data in {"XY", "ORAS"}):
            #    temp[FAT0_offset - 0x4:FAT0_offset] = from_int_little_bytes(biggest_size, 0x4)
    
            #starting from FAT0_offset - 0xC:
            #max of 0x4 and max file size
            #max file size
            #padding (0x4)
           # else:
            write_garc(target, 0x18, (biggest_size_padding).to_bytes(4, byteorder = 'little'))
            write_garc(target, 0x1C, (biggest_size).to_bytes(4, byteorder = 'little'))
            write_garc(target, 0x20, (0x4).to_bytes(4, byteorder = 'little'))

            #write total length of entire GARC
            target.seek(0,2)
            write_garc(target, 0x14, (target.tell()).to_bytes(4, byteorder = 'little'))

        print(f'\tRebuilt the GARC {write_file} from the data in {folder_path}\n')

def main():
    while True:

        match input('''(1) Extract GARCs
(2) Build GARCs
(3) Decompress Folders
(4) Compress Folders
(5) Decompress Files
(6) Compress Files
(Q) Quit\n\n'''
                    ).lower():

            case '1':
                extract_garc(askopenfilenames(title = 'Select GARCs to extract'))
            case '2':
                build_garc(askopendirnames(title = 'Select folders to build into GARCs'))
            case '3':
                decompress_folder(askopendirnames(title = 'Select folders to decompress'))
            case '4':
                compress_folder(askopendirnames(title = 'Select folders to compress'))
            case '5':
                decompress_file(askopenfilenames(title = 'Select files to decompress'))
            case '6':
                compress_file(askopenfilenames(title = 'Select files to compress'))
            case 'q':
                break




if __name__ == '__main__':
    main()