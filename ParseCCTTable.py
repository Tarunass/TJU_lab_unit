#
# lighting_dict = {}
#
# with open("SCR_OctaLight_CCT.txt", "r") as infile:
#     for line in infile:
#         data = line.split()
#         if data[0] == "#CCT":
#             continue
#         CCT = int(data[0])
#         LUX = int(data[1])
#         vals = [float(x) for x in data[2:]]
#         if CCT not in lighting_dict:
#             lighting_dict[CCT] = {LUX: vals}
#         else:
#             lighting_dict[CCT][LUX] = vals
#
#     print(lighting_dict[1800][1250])
#     # print("CCT: %s, LM: %s, vals: %s %s %s %s %s %s %s %s" % tuple(line))
#
# outfile = "ColorTemperature.py"
# with open(outfile, "w") as out:
#     out.write("{ ")
#     for cct in lighting_dict:
#         out.write(str(cct) + ': {\n')
#         for lm in lighting_dict[cct]:
#             out.write(str(lm) + ' : ' + str(lighting_dict[cct][lm]) + ',\n')
#         out.write('},\n')

from ColorTemperature import lighting_dict

print(lighting_dict[1600][25])
