import os
from tkinter.filedialog import askdirectory

def rename_handler(fp, mode):
    
    fillz = 4 if len([name for name in os.listdir(fp) if os.path.isfile(os.path.join(fp, name))]) <= 9999 else 5


    for filename in os.listdir(fp):
        if(not os.path.isdir(os.path.join(fp, filename))):
            #remove leading dec_ and .bin and .lz
            if(filename[:4] == 'dec_'):
                new_name = filename[4:]
            elif(filename[-4:] == '.bin'):
                new_name = filename[:-4]
            elif(filename[-3:] == '.lz'):
                new_name = filename[:-3]
            else:
                new_name = filename
            
            #pad to 5 digits with leading zeroes
            new_name = new_name.zfill(fillz)
        
        
        
            match mode:
                case 'b':
                    new_name = new_name + '.bin'
                case 'c':
                    new_name = 'dec_' + new_name + '.bin'
            if(new_name != filename):
                os.rename(os.path.join(fp, filename), os.path.join(fp, new_name))
    


def main():
    while True:
        mode = input('Select Output:\n\n(a) ABCDE\n(b) ABCDE.bin\n(c) dec_ABCDE.bin\n\n')
        
        if(mode.lower() in {'a', 'b', 'c'}):
            mode.lower()
            break
        else:
            print(f'{mode} is not a valid selection')
        
    
    fp = askdirectory()
    #move up and rename with leading z to avoid overwrite
    
    rename_handler(fp, mode)
    
    
    
if __name__ == '__main__':
    main()
