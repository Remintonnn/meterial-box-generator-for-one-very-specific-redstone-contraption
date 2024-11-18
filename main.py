from nbt_structure_utils import NBTStructure, BlockData, Inventory, ItemStack, Vector
from nbt.nbt import TAG_Compound, TAG_List
import argparse
import os
import json
from tqdm import tqdm
from colorama import init, Fore, Style
from pathlib import Path

# generate a row of chest ready to be pasted onto the machine to use
# but it takes a while compare to other actions,
# so u can disable it here if u are making large amount of map
makeChestRow = True
# idk why would you want to disable this but you can disable the other two sooo
makeBoxGrid = True
# make a json file so u can do something else with the output
makeJSON = False

numOfChest = 12
FillerBlockCount = 143 # the blocks between placing station and corner piston
FillerBlock = "minecraft:polished_blackstone"
# the color shulker would be for each chest
shulkerColors = ["white","light_gray","gray","black","brown","red","orange","yellow","lime","green","cyan","light_blue"]

# blocks not supported by machine, only listing the common ones
Stop_if_black_found = True # throw an error if blackListed block is found
BlackBlockList = ["minecraft:honey_block","minecraft:slime_block","minecraft:redstone_block","minecraft:cobweb","minecraft:brewing_stand","minecraft:jukebox","minecraft:bedrock","minecraft:snow","minecraft:pumpkin","minecraft:melon","minecraft:moss_block","minecraft:beacon","minecraft:sculk_catalyst","minecraft:sculk_shrieker","minecraft:sculk_sensor","minecraft:scaffolding","minecraft:sculk_vein","minecraft:pointed_dripstone","minecraft:decorated_pot","minecraft:glow_lichen","minecraft:sand","minecraft:red_sand","minecraft:gravel","*concrete_powder","*shulker_box","*glazed_terracotta","*slab","*candle","*pressure","trapdoor","*moss", "*carpet", "*leaves", "*glass_pane"]
# grassy block can decay durning moving and require manual fixing after the map is done
grassyBlockList = ["minecraft:grass_block","minecraft:mycelium","minecraft:crimson_nylium","minecraft:warped_nylium"]
# blocks that cannot be recycle/will change state after rercycle, only common ones too
nonRecycleableBlockList = ["minecraft:stone", "minecraft:deepslate", "minecraft:clay", "minecraft:packed_ice", "minecraft:blue_ice", "minecraft:mushroom_stem","minecraft:sea_lantern"]

def main():
    parser = argparse.ArgumentParser(description="file name in input folder or file path)")# and num of chest(defult 12)")
    parser.add_argument("arg1", nargs='?', help="file name in input folder or file path")
    # parser.add_argument("arg2", nargs='?', help="num of chest(defult 12)", default=12)
    
    args = parser.parse_args()
    if args.arg1 == None: args.arg1 = input("pls state the file name of your map nbt file, or just drag the file into this window,\ntype 'ALL' if you want to convert everything in the input folder, nested folder it's fine,\nand it would preserve the folder structure in the output, you have to unzip the files tho\n")
    init()
    if args.arg1 != "ALL": 
        processMapNbt(args.arg1)
    else: 
        inputFolder = Path("input")
        if not inputFolder.exists(): warnMsg("input folder does not exist, create one ant put stuffs in to use this arg",1);return
        for f in inputFolder.rglob("*.nbt"): processMapNbt(str(f), "\\".join(f.relative_to(inputFolder).parts[:-1])+"\\")
    input("\npress enter to exit")

def processMapNbt(fileStr:str, outputDir=""):
    file, fileName = lookForInputFile(fileStr.replace('\"',''))
    if file==None:print("cannot find the file you said");return

    with tqdm(total=100) as progressBar:
        progressBar.set_description("getting block list from map")
        blockList, hasUnsupportedBlock = getBlockList(NBTStructure(file))
        progressBar.update(10)

        if hasUnsupportedBlock and Stop_if_black_found:
            warnMsg("Script stopped due unsupported block, pls generate a map without the red blocks list above,\n or turn this check off by changing the \"Stop_if_black_found\" value in the script",1)
            return

        progressBar.set_description("putting blocks into chests & boxes")
        chestList = getChestList(blockList,numOfChest)
        progressBar.update(10)

        os.makedirs(f"output/{outputDir}", exist_ok=True)
        if makeJSON:
            progressBar.set_description("making json file")
            with open(f"output/{outputDir}{fileName}.json",mode="w+") as f:
                f.write(json.dumps(chestList,indent=2))
        progressBar.update(5)
        createNBTFiles(chestList,fileName,progressBar,outputDir)

def lookForInputFile(fileStr):
    result = None
    fileName = None
    if os.path.isfile(f"{fileStr}.nbt"):
        result = f"{fileStr}.nbt"
    elif os.path.isfile(fileStr):
        result = fileStr
    elif os.path.isfile(f"input/{fileStr}.nbt"):
        result = f"input/{fileStr}.nbt"
    elif os.path.isfile(f"input/{fileStr}"):
        result = f"input/{fileStr}"

    if result!=None:
        fileName = os.path.basename(result)[:-4]
    return result, fileName

# get the metList of map(in the placing order)
def getBlockList(map:NBTStructure):
    maxCoord = map.get_max_coords()
    tqdm.write(f"Map maxCoords: {maxCoord.x} {maxCoord.y} {maxCoord.z}")
    if maxCoord.y>2:# the website will generate 2D map as 3 height nbt
        warnMsg("generate map in 3D usually has wrose result than generate it in 2D if build flat like we're doing here")

    blockList = sorted(map.blocks.values(),key= lambda blockPos: (blockPos.pos.x, -blockPos.pos.z, -blockPos.pos.y))
    seen = {}  # Dictionary to track the best Y for each (X, Z) combination
    for blockPos in blockList:
        if blockPos.pos.z==0: continue #remove the noob line thing
        key = (blockPos.pos.x, blockPos.pos.z)
        if key not in seen or blockPos.pos.y > seen[key].pos.y:
            seen[key] = blockPos

    visitAbleBlocks = list(seen.values())

    pallete = []
    for i in map.palette.get_nbt():
        pallete.append(str(i.get("Name")))
    
    palleteUsed = [0 for i in range(len(pallete))]
    blockList = [FillerBlock for i in range((128-FillerBlockCount)%128)]
    for block in visitAbleBlocks:
        blockList.append(pallete[block.state])
        palleteUsed[block.state] = 1
    for i in range(FillerBlockCount):
        blockList.append(FillerBlock)
    
    for i in range(len(pallete)):
        if palleteUsed[i] == 0: continue
        palleteUsed[i] = checkBlock(pallete[i])

    max_length = max(len(block) for block in pallete)
    tqdm.write("block used in map:")
    for index, block in enumerate(pallete):
        match palleteUsed[index]:
            case 0: continue
            case 1: tqdm.write(f"    {block:<{max_length}}")
            case -1: warnMsg(f"    {block:<{max_length}}    -unsupported",1)
            case -2: warnMsg(f"    {block:<{max_length}}    -grassy     -non recyclable",2)
            case -3: warnMsg(f"    {block:<{max_length}}    -non recyclable",3)
    if -3 in palleteUsed or -2 in palleteUsed:warnMsg(" -None recyclable blocks will get lost/change state after recycle",3)
    if -2 in palleteUsed:warnMsg(" -Grassy blocks has a chance to decay in the blockStream and requires replacing manually once that happended",2)
    if -1 in palleteUsed:warnMsg(" -Unsupported Blocks cannot be transported by blockStream of this machine and WILL break your map",1)
    tqdm.write("")

    return blockList, -1 in palleteUsed

def getChestList(blockList,numOfChest):
    # [
    #     # Chests
    #     [
    #         # Boxes in chest
    #         [
    #             # Items in shulker box
    #             ["minecraft:diamond", 64],
    #             ["minecraft:iron_ingot", 32]
    #         ]
    #     ]
    # ]
    chests = [[[]] for i in range(numOfChest)]
    chestPointer = 0
    totalStackCount = 0; totalBoxCount = 0; totalBlockCount = len(blockList) # just curious
    for block in blockList:
        currentBox = chests[chestPointer][-1]
        if len(currentBox)>0 and currentBox[-1][0]==block and currentBox[-1][1]<64:
            currentBox[-1][1]+=1 # add 1 to current last Stack
        else: # add a new stack
            totalStackCount += 1
            if len(currentBox)<27: # add to current box
                currentBox.append([block,1])
            else: # add a new box
                totalBoxCount += 1
                chests[chestPointer].append([[block,1]])
        chestPointer = (chestPointer+1)%numOfChest
    tqdm.write(f"made {totalBoxCount} box for this map, which is at least {totalBoxCount//numOfChest} box per chest,\nwith {totalStackCount} item stacks, that's {100-int(totalStackCount/totalBlockCount*100)}% compression rate from {totalBlockCount} blocks!\n")
    return chests

def createNBTFiles(chestList,fileName,progressBar:tqdm,outputDir):
    if makeBoxGrid:
        progressBar.set_description("making boxGrid")
        boxGrid = NBTStructure()
        for x, chest in enumerate(chestList):
            for z, box in enumerate(chest):
                boxBlock = f"{shulkerColors[x]}_shulker_box"
                inv = Inventory([ItemStack(item[0],item[1],slot) for slot, item in enumerate(box)])
                boxGrid.set_block(Vector(-x,0,z+(z//9)),BlockData(boxBlock),inv)
        # the libary lie about structure's size if it's above 32, maybe for older version compatibiliby?
        # See the Vector class's get_nbt() method,
        # but litematica(tested in 1.20.4) DOES NOT like being lied to and will fail to load the thing,
        # so here we are, unlie the lies
        # it loads fine in structure block in 1.20.4 too(the bounding box rendering is capped at 48 tho)
        BGnbt = boxGrid.get_nbt()
        trueSize = boxGrid.size()
        for fakeSize in BGnbt.tags:
            if fakeSize.name!="size":continue
            fakeSize[0].value=trueSize.x
            fakeSize[1].value=trueSize.y
            fakeSize[2].value=trueSize.z
            break
        progressBar.set_description("writting boxGrid file")
        BGnbt.write_file(filename=f"output/{outputDir}{fileName}_BoxGrid.nbt")
    progressBar.update(10)

    # doing some NBT shenanigans so I can get box with stuff to appear in chest
    def getBoxStuffTag(box):
        Dummy = TAG_Compound(name="dummy")# They will eat 1 layer of NBT for some reason
        BETag = TAG_Compound(name="BlockEntityTag")
        Inv = TAG_List(name="Items",type=TAG_Compound)
        for slot, item in enumerate(box):
            Inv.tags.append(ItemStack(item[0],item[1],slot).get_nbt())
        BETag.tags.append(Inv)
        Dummy.tags.append(BETag)
        return Dummy
    
    if makeChestRow:
        progressBar.set_description("making ChestRow")
        progressPerChest = 50//numOfChest# progress is at 35% at this point
        chestRow = NBTStructure()
        chestLeft, chestRight = BlockData("chest",[("facing","east"),("type","left")]), BlockData("chest",[("facing","east"),("type","right")])
        for i in range(numOfChest):
            progressBar.set_description(f"making chestRow chest#{i}")
            # the first inv is on which chest depends on the direction they're facing, in this case it's in the right chest
            inv1 = Inventory([ItemStack(f"{shulkerColors[i]}_shulker_box",1,slot,other_tags=getBoxStuffTag(box)) for slot, box in enumerate(chestList[i]) if slot<27])
            inv2 = Inventory([ItemStack(f"{shulkerColors[i]}_shulker_box",1,slot-27,other_tags=getBoxStuffTag(box)) for slot, box in enumerate(chestList[i]) if slot>=27])

            chestRow.set_block(Vector(-i,0,1),chestRight,inv1)
            chestRow.set_block(Vector(-i,0,0),chestLeft,inv2)
            progressBar.update(progressPerChest)
        progressBar.set_description("writting ChestRow file")
        progressBar.n = 85; progressBar.refresh() # force bar to be 85%
        chestRow.get_nbt().write_file(filename=f"output/{outputDir}{fileName}_ChestRow.nbt")

    progressBar.set_description("DONE")
    progressBar.n = progressBar.total; progressBar.refresh() # force bar to be 100%

def checkBlock(block):
    def checkMatch(btc:str):
        if btc.startswith('*'):
            if btc[1:] in block:
                # tqdm.write(f"found {block} maching {btc}")
                return True
        elif block == btc:
            # tqdm.write(f"found {block} == {btc}")
            return True
        return False
    
    for btc in BlackBlockList: # unsupported block
        if checkMatch(btc):return -1

    for btc in grassyBlockList: # grassy block
        if checkMatch(btc):return -2 

    for btc in nonRecycleableBlockList: # non recycleable block
        if checkMatch(btc):return -3 

    return 1 # ok block

def warnMsg(msg:str,level=3):
    match level:
        case 1:tqdm.write(f"{Fore.RED}{Style.BRIGHT}{msg}{Style.RESET_ALL}")
        case _:tqdm.write(f"{Fore.YELLOW}{Style.BRIGHT}{msg}{Style.RESET_ALL}")
        
if __name__ == "__main__":
    main()