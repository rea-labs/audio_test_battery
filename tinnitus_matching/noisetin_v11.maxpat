{
    "patcher": {
        "fileversion": 1,
        "appversion": {
            "major": 9,
            "minor": 1,
            "revision": 4,
            "architecture": "x64",
            "modernui": 1
        },
        "classnamespace": "box",
        "rect": [ 134.0, 134.0, 1915.0, 1192.0 ],
        "style": "default",
        "boxes": [
            {
                "box": {
                    "id": "obj-93",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "float", "int" ],
                    "patching_rect": [ 891.0, 961.5, 114.0, 22.0 ],
                    "text": "maximum 0.000001"
                }
            },
            {
                "box": {
                    "id": "obj-90",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1119.0, 912.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-80",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "float" ],
                    "patching_rect": [ 1017.0, 880.0, 64.0, 22.0 ],
                    "text": "snapshot~"
                }
            },
            {
                "box": {
                    "id": "obj-78",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "patching_rect": [ 1017.0, 921.0, 69.0, 22.0 ],
                    "text": "metro 1000"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-62",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 814.0, 949.0, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-27",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 873.0, 886.0, 117.0, 22.0 ],
                    "text": "expr 20. * log10($f1)"
                }
            },
            {
                "box": {
                    "id": "obj-5",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 784.0, 784.0, 96.0, 22.0 ],
                    "text": "average~ 44100"
                }
            },
            {
                "box": {
                    "id": "obj-57",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 873.0, 510.0, 31.0, 22.0 ],
                    "text": "500"
                }
            },
            {
                "box": {
                    "id": "obj-26",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 881.0, 356.0, 29.5, 22.0 ],
                    "text": "0"
                }
            },
            {
                "box": {
                    "id": "obj-17",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 14.0, 160.0, 150.0, 20.0 ],
                    "text": "filterart"
                }
            },
            {
                "box": {
                    "id": "obj-15",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 292.5, 651.0, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-102",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 369.75, 602.0, 29.5, 22.0 ],
                    "text": "64"
                }
            },
            {
                "box": {
                    "id": "obj-99",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 758.0, 179.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-95",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 790.0, 179.0, 150.0, 20.0 ],
                    "text": "init"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-91",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 608.0, 246.0, 29.5, 22.0 ],
                    "text": "0.5"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-87",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 72.75, 136.0, 29.5, 22.0 ],
                    "text": "5"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-84",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 206.0, 575.0, 29.5, 22.0 ],
                    "text": "64"
                }
            },
            {
                "box": {
                    "id": "obj-79",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 146.0, 636.0, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-76",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 408.0, 312.5, 37.0, 22.0 ],
                    "text": "1000"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-71",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1315.0, 859.0, 100.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-67",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1376.5, 371.0, 37.0, 22.0 ],
                    "text": "8000"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-60",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 129.125, 230.0, 53.0, 22.0 ],
                    "style": "chiba"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-11",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1109.5, 768.5, 103.0, 20.0 ],
                    "text": "filter out note-offs"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-13",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1349.0, 604.5, 119.0, 20.0 ],
                    "text": "input from controller"
                }
            },
            {
                "box": {
                    "activecolor": [ 0.952941, 0.564706, 0.098039, 1.0 ],
                    "disabled": [ 0, 0, 0, 0, 0 ],
                    "flagmode": 1,
                    "hidden": 1,
                    "id": "obj-14",
                    "itemtype": 0,
                    "maxclass": "radiogroup",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1333.0, 968.0, 18.0, 82.0 ],
                    "shape": 1,
                    "size": 5,
                    "value": 5
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-39",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1278.0, 972.5, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-16",
                    "maxclass": "newobj",
                    "numinlets": 5,
                    "numoutlets": 4,
                    "outlettype": [ "int", "", "", "int" ],
                    "patching_rect": [ 1270.5, 929.5, 71.0, 22.0 ],
                    "text": "counter 7 9"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-18",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1278.0, 896.5, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-25",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1182.0, 959.5, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-30",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1284.0, 768.5, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-33",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1217.0, 768.5, 34.0, 22.0 ],
                    "text": "gate"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-35",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 1284.0, 733.5, 29.5, 22.0 ],
                    "text": "> 0"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-36",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1284.0, 697.5, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-41",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1182.0, 896.5, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-54",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1305.0, 820.5, 45.0, 20.0 ],
                    "text": "notenr"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-55",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 3,
                    "outlettype": [ "bang", "bang", "" ],
                    "patching_rect": [ 1217.0, 820.5, 62.0, 22.0 ],
                    "text": "select 0 4"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-59",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1232.0, 697.5, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-1",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "int", "int", "int" ],
                    "patching_rect": [ 1232.0, 604.5, 107.0, 22.0 ],
                    "text": "notein"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-135",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1068.0, 646.0, 250.0, 20.0 ],
                    "text": "add relative fine tune to absolute coarse tune"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-140",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1315.0, 395.0, 131.0, 20.0 ],
                    "text": "min / max of full range"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-143",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "float" ],
                    "patching_rect": [ 1315.0, 497.0, 41.0, 22.0 ],
                    "text": "/ 127."
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-144",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 1315.0, 466.0, 29.5, 22.0 ],
                    "text": "!- 0"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-145",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1315.0, 422.0, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-146",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1373.5, 423.0, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-43",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1254.0, 527.0, 172.0, 20.0 ],
                    "text": "scale to stepsize of full range?"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-147",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 972.0, 491.0, 153.0, 20.0 ],
                    "text": "scale to desired freq range"
                }
            },
            {
                "box": {
                    "format": 6,
                    "hidden": 1,
                    "id": "obj-40",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1005.0, 687.0, 87.0, 22.0 ]
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-148",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "float" ],
                    "patching_rect": [ 1028.0, 605.0, 31.0, 22.0 ],
                    "text": "t b f"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-37",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "float" ],
                    "patching_rect": [ 1005.0, 646.0, 54.0, 22.0 ],
                    "text": "+ 0."
                }
            },
            {
                "box": {
                    "format": 6,
                    "hidden": 1,
                    "id": "obj-34",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1142.0, 565.0, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "hidden": 1,
                    "id": "obj-150",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1005.0, 565.0, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-29",
                    "maxclass": "newobj",
                    "numinlets": 6,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1142.0, 527.0, 136.0, 22.0 ],
                    "text": "scale 0 127 -1000 1000"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-28",
                    "maxclass": "newobj",
                    "numinlets": 6,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 979.5, 527.0, 159.0, 22.0 ],
                    "text": "scale 0 127 10. 16000. 1.06"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-24",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1142.0, 363.0, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-23",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1005.0, 363.0, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-151",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 1156.0, 209.0, 39.0, 22.0 ],
                    "text": "zl rev"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-152",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1156.0, 170.0, 36.0, 22.0 ],
                    "text": "pack"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-153",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 3,
                    "outlettype": [ "", "", "" ],
                    "patching_rect": [ 1156.0, 246.0, 58.0, 22.0 ],
                    "text": "route 0 3"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-154",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1243.0, 246.0, 47.0, 20.0 ],
                    "text": "ctl nr."
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-3",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "int", "int", "int" ],
                    "patching_rect": [ 1156.0, 121.0, 53.0, 22.0 ],
                    "text": "ctlin"
                }
            },
            {
                "box": {
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "hidden": 1,
                    "id": "obj-160",
                    "maxclass": "newobj",
                    "numinlets": 6,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 420.5, 145.0, 125.0, 22.0 ],
                    "text": "scale 0 127 1 25 1.06"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-159",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "int", "int" ],
                    "patching_rect": [ 389.0, 77.0, 42.0, 22.0 ],
                    "text": "ctlin 7"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-141",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 515.0, 170.0, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "hidden": 1,
                    "id": "obj-136",
                    "maxclass": "newobj",
                    "numinlets": 6,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 171.5, 95.0, 72.0, 22.0 ],
                    "text": "scale 0 127"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-137",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "int", "int" ],
                    "patching_rect": [ 225.5, 64.0, 42.0, 22.0 ],
                    "text": "ctlin 3"
                }
            },
            {
                "box": {
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "hidden": 1,
                    "id": "obj-133",
                    "maxclass": "newobj",
                    "numinlets": 6,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 301.5, 145.0, 105.0, 22.0 ],
                    "text": "scale 0 127 0 9 1."
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-134",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "int", "int" ],
                    "patching_rect": [ 420.5, 105.0, 49.0, 22.0 ],
                    "text": "ctlin 17"
                }
            },
            {
                "box": {
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "hidden": 1,
                    "id": "obj-125",
                    "maxclass": "newobj",
                    "numinlets": 6,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 115.5, 145.0, 159.0, 22.0 ],
                    "text": "scale 0 127 50. 16000. 1.06"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-119",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "int", "int" ],
                    "patching_rect": [ 115.5, 83.0, 42.0, 22.0 ],
                    "text": "ctlin 0"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-82",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "int", "int" ],
                    "patching_rect": [ 100.0, 594.0, 42.0, 22.0 ],
                    "text": "ctlin 4"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-22",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "int", "int" ],
                    "patching_rect": [ 199.75, 636.0, 42.0, 22.0 ],
                    "text": "ctlin 2"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-12",
                    "maxclass": "newobj",
                    "numinlets": 4,
                    "numoutlets": 2,
                    "outlettype": [ "signal", "signal" ],
                    "patching_rect": [ 75.75, 637.0, 50.5, 22.0 ],
                    "text": "pan2",
                    "varname": "pannr-patch"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-10",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 296.5, 602.0, 42.0, 22.0 ],
                    "text": "midiin"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-9",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "int", "int", "int" ],
                    "patching_rect": [ 447.0, 408.0, 43.0, 22.0 ],
                    "text": "notein"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-77",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 425.5, 978.0, 150.0, 20.0 ],
                    "text": "Lautstärke gesamt"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-70",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 10.5, 882.0, 150.0, 20.0 ],
                    "text": "speichern"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-68",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 19.5, 820.0, 150.0, 20.0 ],
                    "text": "Ton an/aus"
                }
            },
            {
                "box": {
                    "id": "obj-66",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 347.5, 651.0, 150.0, 20.0 ],
                    "text": "< Lautstärke"
                }
            },
            {
                "box": {
                    "id": "obj-65",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 206.0, 637.0, 150.0, 20.0 ],
                    "text": "< panning"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-58",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 518.5, 575.0, 150.0, 20.0 ],
                    "text": "< stumm"
                }
            },
            {
                "box": {
                    "id": "obj-21",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 315.5, 200.0, 98.0, 20.0 ],
                    "text": "Filterbandbreite"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-20",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 212.5, 200.0, 90.0, 20.0 ],
                    "text": "Filteramplitude"
                }
            },
            {
                "box": {
                    "id": "obj-19",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 129.125, 200.0, 83.75, 20.0 ],
                    "text": "Filterfrequenz"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-8",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 472.0, 239.0, 46.0, 22.0 ],
                    "text": "noise~"
                }
            },
            {
                "box": {
                    "fontname": "Courier Bold",
                    "fontsize": 36.0,
                    "hidden": 1,
                    "id": "obj-118",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 14.0, 12.0, 406.0, 50.0 ],
                    "text": "NOISETIN"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-116",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 4,
                    "outlettype": [ "signal", "signal", "list", "list" ],
                    "patching_rect": [ 301.5, 882.0, 87.0, 22.0 ],
                    "text": "omx.peaklim~"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-112",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 83.5, 882.0, 150.0, 20.0 ],
                    "text": "laden"
                }
            },
            {
                "box": {
                    "attr": "edit_mode",
                    "id": "obj-110",
                    "lock": 1,
                    "maxclass": "attrui",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "orientation": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 10.5, 181.0, 103.0, 44.0 ],
                    "style": "chiba",
                    "text_width": 83.0
                }
            },
            {
                "box": {
                    "fontname": "Arial Bold",
                    "fontsize": 14.0,
                    "hidden": 1,
                    "id": "obj-108",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 19.5, 296.0, 136.0, 23.0 ],
                    "text": "Rauschen 3"
                }
            },
            {
                "box": {
                    "fontname": "Arial",
                    "fontsize": 13.0,
                    "id": "obj-52",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 83.5, 1005.5, 29.5, 23.0 ],
                    "text": "4"
                }
            },
            {
                "box": {
                    "fontname": "Arial",
                    "fontsize": 13.0,
                    "id": "obj-49",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 83.5, 972.5, 29.5, 23.0 ],
                    "text": "3"
                }
            },
            {
                "box": {
                    "fontname": "Arial",
                    "fontsize": 13.0,
                    "id": "obj-38",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 5.5, 1006.5, 50.0, 23.0 ],
                    "text": "store 4"
                }
            },
            {
                "box": {
                    "fontname": "Arial",
                    "fontsize": 13.0,
                    "id": "obj-32",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 5.5, 976.5, 50.0, 23.0 ],
                    "text": "store 3"
                }
            },
            {
                "box": {
                    "fontname": "Arial",
                    "fontsize": 13.0,
                    "id": "obj-31",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 5.5, 944.5, 50.0, 23.0 ],
                    "text": "store 2"
                }
            },
            {
                "box": {
                    "fontname": "Arial",
                    "fontsize": 13.0,
                    "hidden": 1,
                    "id": "obj-50",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 603.0, 904.5, 141.0, 23.0 ],
                    "text": "print stored @popup 1"
                }
            },
            {
                "box": {
                    "fontname": "Arial",
                    "fontsize": 13.0,
                    "hidden": 1,
                    "id": "obj-46",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 603.0, 929.5, 151.0, 23.0 ],
                    "text": "print recalled @popup 1"
                }
            },
            {
                "box": {
                    "fontname": "Arial",
                    "fontsize": 13.0,
                    "hidden": 1,
                    "id": "obj-2",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 603.0, 989.5, 51.0, 23.0 ],
                    "text": "clear 2"
                }
            },
            {
                "box": {
                    "fontname": "Arial",
                    "fontsize": 13.0,
                    "hidden": 1,
                    "id": "obj-53",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 35.5, 1062.0, 53.0, 23.0 ],
                    "text": "clearall"
                }
            },
            {
                "box": {
                    "fontname": "Arial",
                    "fontsize": 13.0,
                    "id": "obj-42",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 83.5, 942.5, 29.5, 23.0 ],
                    "text": "2"
                }
            },
            {
                "box": {
                    "fontname": "Arial",
                    "fontsize": 13.0,
                    "id": "obj-44",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 83.5, 909.5, 29.5, 23.0 ],
                    "text": "1"
                }
            },
            {
                "box": {
                    "fontname": "Arial",
                    "fontsize": 13.0,
                    "id": "obj-45",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 5.5, 914.5, 51.0, 23.0 ],
                    "text": "store 1"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-142",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "signal", "signal" ],
                    "patching_rect": [ 206.0, 956.0, 47.0, 22.0 ],
                    "text": "zerox~"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-85",
                    "maxclass": "preset",
                    "numinlets": 1,
                    "numoutlets": 5,
                    "outlettype": [ "preset", "int", "preset", "int", "" ],
                    "patching_rect": [ 323.5, 997.0, 100.0, 40.0 ],
                    "preset_data": [
                        {
                            "number": 1,
                            "data": [ 6, "obj-47", "gain~", "list", 157, 10.0, 6, "obj-48", "gain~", "list", 157, 10.0, 5, "obj-81", "filtergraph~", "nfilters", 1, 9, "obj-81", "filtergraph~", "setoptions", 0, 3, 0, 0, 0, 8, "obj-81", "filtergraph~", "params", 0, 9181.0, 1.0, 25.0, 5, "obj-75", "number", "float", 9181.0, 5, "obj-74", "number", "float", 1.0, 5, "obj-72", "number", "float", 188.699997 ]
                        },
                        {
                            "number": 2,
                            "data": [ 6, "obj-47", "gain~", "list", 80, 80.0, 6, "obj-48", "gain~", "list", 80, 34.0, 5, "obj-81", "filtergraph~", "nfilters", 1, 9, "obj-81", "filtergraph~", "setoptions", 0, 3, 0, 0, 0, 8, "obj-81", "filtergraph~", "params", 0, 2466.209473, 1.0, 3.336939, 5, "obj-75", "number", "float", 0.0, 5, "obj-74", "number", "float", 0.0, 5, "obj-72", "number", "float", 3.336939, 5, "obj-23", "number", "int", 93, 5, "obj-24", "number", "int", 32, 5, "obj-150", "number", "float", 2215.209473, 5, "obj-34", "number", "float", 251.0, 5, "obj-40", "number", "float", 2466.209473, 5, "obj-146", "number", "int", 0, 5, "obj-145", "number", "int", 0, 5, "obj-59", "number", "int", 0, 5, "obj-36", "number", "int", 0, 5, "obj-30", "toggle", "int", 0, 5, "obj-25", "toggle", "int", 1, 5, "obj-39", "number", "int", 3, 5, "obj-14", "radiogroup", "int", 3, 5, "obj-60", "number", "float", 2466.209473, 5, "obj-79", "number", "int", 56 ]
                        },
                        {
                            "number": 3,
                            "data": [ 6, "obj-47", "gain~", "list", 80, 80.0, 6, "obj-48", "gain~", "list", 80, 34.0, 5, "obj-81", "filtergraph~", "nfilters", 1, 9, "obj-81", "filtergraph~", "setoptions", 0, 3, 0, 0, 0, 8, "obj-81", "filtergraph~", "params", 0, 2466.209473, 1.0, 3.336939, 5, "obj-75", "number", "float", 0.0, 5, "obj-74", "number", "float", 0.0, 5, "obj-72", "number", "float", 3.336939, 5, "obj-23", "number", "int", 93, 5, "obj-24", "number", "int", 32, 5, "obj-150", "number", "float", 2215.209473, 5, "obj-34", "number", "float", 251.0, 5, "obj-40", "number", "float", 2466.209473, 5, "obj-146", "number", "int", 0, 5, "obj-145", "number", "int", 0, 5, "obj-59", "number", "int", 0, 5, "obj-36", "number", "int", 0, 5, "obj-30", "toggle", "int", 0, 5, "obj-25", "toggle", "int", 1, 5, "obj-39", "number", "int", 3, 5, "obj-14", "radiogroup", "int", 3, 5, "obj-60", "number", "float", 2466.209473, 5, "obj-79", "number", "int", 56 ]
                        },
                        {
                            "number": 4,
                            "data": [ 6, "obj-47", "gain~", "list", 78, 78.0, 6, "obj-48", "gain~", "list", 78, 34.0, 5, "obj-81", "filtergraph~", "nfilters", 1, 9, "obj-81", "filtergraph~", "setoptions", 0, 3, 0, 0, 0, 8, "obj-81", "filtergraph~", "params", 0, 1735.59082, 1.0, 7.298883, 5, "obj-75", "number", "float", 0.0, 5, "obj-74", "number", "float", 0.0, 5, "obj-72", "number", "float", 7.298883, 5, "obj-23", "number", "int", 86, 5, "obj-24", "number", "int", 33, 5, "obj-150", "number", "float", 1476.59082, 5, "obj-34", "number", "float", 259.0, 5, "obj-40", "number", "float", 1735.59082, 5, "obj-146", "number", "int", 0, 5, "obj-145", "number", "int", 0, 5, "obj-59", "number", "int", 0, 5, "obj-36", "number", "int", 0, 5, "obj-30", "toggle", "int", 0, 5, "obj-25", "toggle", "int", 1, 5, "obj-39", "number", "int", 3, 5, "obj-14", "radiogroup", "int", 3, 5, "obj-60", "number", "float", 1735.59082, 5, "obj-79", "number", "int", 53 ]
                        }
                    ],
                    "style": "chiba"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-83",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 46.5, 83.0, 47.0, 22.0 ],
                    "style": "chiba",
                    "text": "noise~"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-4",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 19.5, 307.0, 333.0, 22.0 ],
                    "style": "chiba",
                    "text": "0.020599 0. -0.020599 -1.915832 0.917603"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-72",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 358.0, 224.5, 53.0, 22.0 ],
                    "style": "chiba"
                }
            },
            {
                "box": {
                    "format": 6,
                    "hidden": 1,
                    "id": "obj-74",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 225.5, 230.0, 53.0, 22.0 ],
                    "style": "chiba"
                }
            },
            {
                "box": {
                    "format": 6,
                    "hidden": 1,
                    "id": "obj-75",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 305.5, 64.0, 54.0, 22.0 ],
                    "style": "chiba"
                }
            },
            {
                "box": {
                    "autoout": 1,
                    "domain": [ 0.0, 22050.0 ],
                    "fontface": 0,
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "id": "obj-81",
                    "maxclass": "filtergraph~",
                    "nfilters": 1,
                    "numinlets": 8,
                    "numoutlets": 7,
                    "outlettype": [ "list", "float", "float", "float", "float", "list", "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 31.0, 424.0, 360.0, 155.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 26.5, 415.5, 360.0, 155.0 ],
                    "setfilter": [ 0, 8, 0, 0, 0, 301.6791076660156, 1.0, 0.5, 9.999999747378752e-05, 22050.0, 9.999999747378752e-05, 16.0, 0.5, 25.0 ],
                    "style": "chiba"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-63",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 14.0, 128.5, 41.0, 22.0 ],
                    "style": "chiba",
                    "text": "clear"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-6",
                    "maxclass": "newobj",
                    "numinlets": 6,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 684.5, 723.0, 87.0, 22.0 ],
                    "style": "chiba",
                    "text": "biquad~"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-56",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "signal", "signal" ],
                    "patching_rect": [ 684.5, 467.0, 118.0, 22.0 ],
                    "style": "chiba",
                    "text": "windowed-fft~ 1024"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-48",
                    "interp": 34.0,
                    "interpinlet": 1,
                    "maxclass": "gain~",
                    "multichannelvariant": 0,
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "signal", "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 120.0, 716.0, 22.0, 140.0 ],
                    "style": "chiba"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-47",
                    "interp": 127.0,
                    "interpinlet": 1,
                    "maxclass": "gain~",
                    "multichannelvariant": 0,
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "signal", "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 83.5, 716.0, 22.0, 140.0 ],
                    "style": "chiba"
                }
            },
            {
                "box": {
                    "hidden": 1,
                    "id": "obj-7",
                    "local": 1,
                    "maxclass": "ezdac~",
                    "numinlets": 2,
                    "numoutlets": 0,
                    "patching_rect": [ 413.0, 780.0, 44.0, 44.0 ],
                    "prototypename": "helpfile",
                    "style": "chiba"
                }
            },
            {
                "box": {
                    "background": 1,
                    "id": "obj-51",
                    "maxclass": "spectroscope~",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 408.0, 415.5, 352.0, 144.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 695.0, 541.0, 333.0, 142.0 ],
                    "style": "chiba"
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "destination": [ "obj-36", 0 ],
                    "hidden": 1,
                    "source": [ "obj-1", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-59", 0 ],
                    "hidden": 1,
                    "source": [ "obj-1", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-9", 0 ],
                    "hidden": 1,
                    "source": [ "obj-10", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-47", 0 ],
                    "hidden": 1,
                    "order": 1,
                    "source": [ "obj-102", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-48", 0 ],
                    "hidden": 1,
                    "order": 0,
                    "source": [ "obj-102", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-81", 0 ],
                    "hidden": 1,
                    "source": [ "obj-110", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-7", 1 ],
                    "hidden": 1,
                    "source": [ "obj-116", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-7", 0 ],
                    "hidden": 1,
                    "source": [ "obj-116", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-47", 0 ],
                    "hidden": 1,
                    "source": [ "obj-12", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-48", 0 ],
                    "hidden": 1,
                    "source": [ "obj-12", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-75", 0 ],
                    "hidden": 1,
                    "source": [ "obj-125", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-21", 0 ],
                    "hidden": 1,
                    "source": [ "obj-133", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-160", 0 ],
                    "hidden": 1,
                    "source": [ "obj-134", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-75", 0 ],
                    "hidden": 1,
                    "source": [ "obj-136", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-136", 0 ],
                    "hidden": 1,
                    "source": [ "obj-137", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-29", 4 ],
                    "hidden": 1,
                    "source": [ "obj-143", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-143", 0 ],
                    "hidden": 1,
                    "source": [ "obj-144", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-144", 0 ],
                    "hidden": 1,
                    "order": 0,
                    "source": [ "obj-145", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-28", 3 ],
                    "hidden": 1,
                    "order": 1,
                    "source": [ "obj-145", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-144", 1 ],
                    "hidden": 1,
                    "order": 0,
                    "source": [ "obj-146", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-28", 4 ],
                    "hidden": 1,
                    "order": 1,
                    "source": [ "obj-146", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-37", 1 ],
                    "hidden": 1,
                    "source": [ "obj-148", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-37", 0 ],
                    "hidden": 1,
                    "source": [ "obj-148", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-37", 0 ],
                    "hidden": 1,
                    "source": [ "obj-150", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-153", 0 ],
                    "hidden": 1,
                    "source": [ "obj-151", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-151", 0 ],
                    "hidden": 1,
                    "source": [ "obj-152", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-23", 0 ],
                    "hidden": 1,
                    "source": [ "obj-153", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-24", 0 ],
                    "hidden": 1,
                    "source": [ "obj-153", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-160", 0 ],
                    "hidden": 1,
                    "source": [ "obj-159", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-110", 0 ],
                    "hidden": 1,
                    "order": 2,
                    "source": [ "obj-16", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-14", 0 ],
                    "hidden": 1,
                    "order": 0,
                    "source": [ "obj-16", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-18", 0 ],
                    "hidden": 1,
                    "order": 1,
                    "source": [ "obj-16", 3 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-39", 0 ],
                    "hidden": 1,
                    "order": 1,
                    "source": [ "obj-16", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-71", 0 ],
                    "hidden": 1,
                    "order": 0,
                    "source": [ "obj-16", 3 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-72", 0 ],
                    "hidden": 1,
                    "source": [ "obj-160", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-16", 0 ],
                    "hidden": 1,
                    "source": [ "obj-18", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-85", 0 ],
                    "hidden": 1,
                    "source": [ "obj-2", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-47", 1 ],
                    "hidden": 1,
                    "order": 1,
                    "source": [ "obj-22", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-47", 0 ],
                    "hidden": 1,
                    "order": 2,
                    "source": [ "obj-22", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-48", 0 ],
                    "hidden": 1,
                    "order": 0,
                    "source": [ "obj-22", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-28", 0 ],
                    "hidden": 1,
                    "source": [ "obj-23", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-29", 0 ],
                    "hidden": 1,
                    "source": [ "obj-24", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-7", 0 ],
                    "hidden": 1,
                    "source": [ "obj-25", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-34", 0 ],
                    "source": [ "obj-26", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-62", 0 ],
                    "source": [ "obj-27", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-150", 0 ],
                    "hidden": 1,
                    "source": [ "obj-28", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-34", 0 ],
                    "hidden": 1,
                    "source": [ "obj-29", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-152", 1 ],
                    "hidden": 1,
                    "source": [ "obj-3", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-152", 0 ],
                    "hidden": 1,
                    "source": [ "obj-3", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-85", 0 ],
                    "hidden": 1,
                    "source": [ "obj-31", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-85", 0 ],
                    "hidden": 1,
                    "source": [ "obj-32", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-55", 0 ],
                    "hidden": 1,
                    "source": [ "obj-33", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-148", 0 ],
                    "hidden": 1,
                    "source": [ "obj-34", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-30", 0 ],
                    "hidden": 1,
                    "order": 0,
                    "source": [ "obj-35", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-33", 0 ],
                    "hidden": 1,
                    "order": 1,
                    "source": [ "obj-35", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-35", 0 ],
                    "hidden": 1,
                    "source": [ "obj-36", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-40", 0 ],
                    "hidden": 1,
                    "order": 0,
                    "source": [ "obj-37", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-81", 5 ],
                    "hidden": 1,
                    "order": 1,
                    "source": [ "obj-37", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-85", 0 ],
                    "hidden": 1,
                    "source": [ "obj-38", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-25", 0 ],
                    "hidden": 1,
                    "source": [ "obj-41", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-85", 0 ],
                    "hidden": 1,
                    "source": [ "obj-42", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-85", 0 ],
                    "hidden": 1,
                    "source": [ "obj-44", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-85", 0 ],
                    "hidden": 1,
                    "source": [ "obj-45", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-116", 0 ],
                    "hidden": 1,
                    "order": 2,
                    "source": [ "obj-47", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-51", 0 ],
                    "hidden": 1,
                    "order": 1,
                    "source": [ "obj-47", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-56", 0 ],
                    "hidden": 1,
                    "order": 0,
                    "source": [ "obj-47", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-116", 1 ],
                    "hidden": 1,
                    "order": 1,
                    "source": [ "obj-48", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-15", 0 ],
                    "hidden": 1,
                    "source": [ "obj-48", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-51", 0 ],
                    "hidden": 1,
                    "order": 0,
                    "source": [ "obj-48", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-85", 0 ],
                    "hidden": 1,
                    "source": [ "obj-49", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-80", 0 ],
                    "source": [ "obj-5", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-85", 0 ],
                    "hidden": 1,
                    "source": [ "obj-52", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-85", 0 ],
                    "hidden": 1,
                    "source": [ "obj-53", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-18", 0 ],
                    "hidden": 1,
                    "source": [ "obj-55", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-41", 0 ],
                    "hidden": 1,
                    "source": [ "obj-55", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-51", 0 ],
                    "hidden": 1,
                    "source": [ "obj-56", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-150", 0 ],
                    "source": [ "obj-57", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-33", 1 ],
                    "hidden": 1,
                    "source": [ "obj-59", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-12", 0 ],
                    "hidden": 1,
                    "order": 1,
                    "source": [ "obj-6", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-5", 0 ],
                    "order": 0,
                    "source": [ "obj-6", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-6", 0 ],
                    "hidden": 1,
                    "source": [ "obj-63", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-146", 0 ],
                    "hidden": 1,
                    "source": [ "obj-67", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-81", 7 ],
                    "hidden": 1,
                    "source": [ "obj-72", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-81", 6 ],
                    "hidden": 1,
                    "source": [ "obj-74", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-136", 3 ],
                    "hidden": 1,
                    "source": [ "obj-75", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-60", 0 ],
                    "hidden": 1,
                    "source": [ "obj-76", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-80", 1 ],
                    "source": [ "obj-78", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-12", 2 ],
                    "hidden": 1,
                    "source": [ "obj-79", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-6", 0 ],
                    "hidden": 1,
                    "source": [ "obj-8", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-78", 0 ],
                    "order": 0,
                    "source": [ "obj-80", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-93", 0 ],
                    "order": 1,
                    "source": [ "obj-80", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-4", 1 ],
                    "hidden": 1,
                    "order": 1,
                    "source": [ "obj-81", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-6", 0 ],
                    "hidden": 1,
                    "order": 0,
                    "source": [ "obj-81", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-60", 0 ],
                    "hidden": 1,
                    "source": [ "obj-81", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-12", 2 ],
                    "hidden": 1,
                    "order": 1,
                    "source": [ "obj-82", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-79", 0 ],
                    "hidden": 1,
                    "order": 0,
                    "source": [ "obj-82", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-6", 0 ],
                    "hidden": 1,
                    "source": [ "obj-83", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-79", 0 ],
                    "hidden": 1,
                    "source": [ "obj-84", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-46", 0 ],
                    "hidden": 1,
                    "source": [ "obj-85", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-50", 0 ],
                    "hidden": 1,
                    "source": [ "obj-85", 3 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-110", 0 ],
                    "hidden": 1,
                    "source": [ "obj-87", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-78", 0 ],
                    "source": [ "obj-90", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-72", 0 ],
                    "hidden": 1,
                    "source": [ "obj-91", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-27", 0 ],
                    "source": [ "obj-93", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-102", 0 ],
                    "hidden": 1,
                    "order": 4,
                    "source": [ "obj-99", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-26", 0 ],
                    "order": 0,
                    "source": [ "obj-99", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-57", 0 ],
                    "order": 1,
                    "source": [ "obj-99", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-76", 0 ],
                    "hidden": 1,
                    "order": 3,
                    "source": [ "obj-99", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-84", 0 ],
                    "hidden": 1,
                    "order": 5,
                    "source": [ "obj-99", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-87", 0 ],
                    "hidden": 1,
                    "order": 6,
                    "source": [ "obj-99", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-91", 0 ],
                    "hidden": 1,
                    "order": 2,
                    "source": [ "obj-99", 0 ]
                }
            }
        ],
        "autosave": 0
    }
}