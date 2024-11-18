from nbt_structure_utils import *
from tqdm import tqdm
from colorama import *
from nbt.nbt import *

def main():
    structure_file = NBTFile()
    size = Vector(1, 1, 123)
    print(structure_file.tags)
    structure_file.tags.append(size.get_nbt("size"))
    structure_file.tags.append(Vector(8,7,8).get_nbt("trash"));structure_file.tags.append(Vector(8,7,8).get_nbt("trash"));structure_file.tags.append(Vector(8,7,8).get_nbt("trash"))
    for tag in structure_file.tags:
        if tag.name!="size":continue
        tag[0].value=12
    print(structure_file.pretty_tree())

if __name__ == "__main__":
    main()