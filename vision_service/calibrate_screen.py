import tkinter as tk
import json

coords = {}

def on_press(event):
    coords['x1'] = event.x
    coords['y1'] = event.y

def on_drag(event):
    canvas.delete("box")
    canvas.create_rectangle(coords['x1'], coords['y1'], event.x, event.y,
                            outline='lime', width=2, tag="box")

def on_release(event):
    coords['x2'] = event.x
    coords['y2'] = event.y

    result = {
        "left": min(coords['x1'], coords['x2']),
        "top": min(coords['y1'], coords['y2']),
        "width": abs(coords['x2'] - coords['x1']),
        "height": abs(coords['y2'] - coords['y1'])
    }

    with open("calibration.json", "w") as f:
        json.dump(result, f, indent=2)

    root.destroy()

root = tk.Tk()
root.attributes("-fullscreen", True)
root.attributes("-alpha", 0.3)
root.configure(bg="black")

canvas = tk.Canvas(root, bg="black", highlightthickness=0)
canvas.pack(fill="both", expand=True)

canvas.bind("<ButtonPress-1>", on_press)
canvas.bind("<B1-Motion>", on_drag)
canvas.bind("<ButtonRelease-1>", on_release)

root.mainloop()
