import threading
import time
import random
import tkinter as tk
import sys


class Buffer:
    def __init__(self, size=20):
        self.buffer = [0] * size
        self.size = size
        self.in_pos = 0
        self.out_pos = 0
        self.mutex = threading.Lock()
        self.empty = threading.Semaphore(size)
        self.full = threading.Semaphore(0)
        self.producer_pos = 0
        self.consumer_pos = 0

    def produce(self, data):
        self.empty.acquire()
        self.mutex.acquire()
        self.buffer[self.in_pos] = data
        self.in_pos = (self.in_pos + 1) % self.size
        self.producer_pos = self.in_pos
        self.mutex.release()
        self.full.release()

    def consume(self):
        self.full.acquire()
        self.mutex.acquire()
        data = self.buffer[self.out_pos]
        self.out_pos = (self.out_pos + 1) % self.size
        self.consumer_pos = self.out_pos
        self.mutex.release()
        self.empty.release()
        return data

    def get_producer_pos(self):
        return self.producer_pos

    def get_consumer_pos(self):
        return self.consumer_pos


class Producer(threading.Thread):
    def __init__(self, buffer, id):
        threading.Thread.__init__(self)
        self.buffer = buffer
        self.id = id

    def run(self):
        while True:
            data = random.randint(1, self.buffer.size)
            self.buffer.produce(data)
            print("Producer %d produced: %d\n" % (self.id, data))
            time.sleep(random.randint(1, 3))


class Consumer(threading.Thread):
    def __init__(self, buffer, id):
        threading.Thread.__init__(self)
        self.buffer = buffer
        self.id = id

    def run(self):
        while True:
            data = self.buffer.consume()
            print("Consumer %d consumed: %d\n" % (self.id, data))
            time.sleep(random.randint(1, 3))


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.buffer_size = tk.IntVar(value=20)
        self.buffer = Buffer(size=self.buffer_size.get())
        self.producers = []
        self.consumers = []
        self.create_widgets()
        self.pack()

        # Start updating GUI
        self.update_gui()

    def create_widgets(self):
        # Change the title of the main window
        self.master.title('Producer-Consumer Problem')

        # Create a frame to contain the buffer size label and scale
        buffer_frame = tk.Frame(self)
        buffer_frame.pack(side=tk.TOP, pady=1)

        # Create the scale to adjust buffer size
        self.buffer_size_label = tk.Label(buffer_frame, text="Buffer Size:")
        self.buffer_size_label.pack(side=tk.LEFT)

        self.buffer_size_scale = tk.Scale(buffer_frame, from_=1, to=30, orient=tk.HORIZONTAL,
                                          variable=self.buffer_size,
                                          command=self.change_buffer_size)
        self.buffer_size_scale.pack(side=tk.LEFT)

        # Create a canvas to display buffer contents
        self.buffer_canvas = tk.Canvas(self, width=400, height=100)
        self.buffer_canvas.pack()

        # Create the labels to display current positions
        self.producer_label = tk.Label(self, text="Producer: ")
        self.producer_label.pack()
        self.consumer_label = tk.Label(self, text="Consumer: ")
        self.consumer_label.pack()

    def draw_buffer(self):
        # Clear the canvas
        self.buffer_canvas.delete("all")

        # Get the size of the canvas and the buffer
        canvas_width = self.buffer_canvas.winfo_width()
        canvas_height = self.buffer_canvas.winfo_height()
        buffer_size = self.buffer_size.get()

        # Compute the size of each cell
        cell_width = canvas_width // buffer_size
        cell_height = canvas_height // 2

        # Compute the font size based on the cell size
        font_size = min(cell_width, cell_height) // 2

        # Draw the buffer cells and labels
        for i in range(buffer_size):
            cell_x1 = i * cell_width
            cell_x2 = (i + 1) * cell_width
            cell_y1 = 0
            cell_y2 = cell_height
            cell_color = "lightgray"
            if i == self.buffer.in_pos:
                cell_color = "green"
            elif i == self.buffer.out_pos:
                cell_color = "red"
            self.buffer_canvas.create_rectangle(cell_x1, cell_y1, cell_x2, cell_y2, fill=cell_color)

            cell_x1 = i * cell_width
            cell_x2 = (i + 1) * cell_width
            cell_y1 = cell_height
            cell_y2 = 2 * cell_height
            cell_color = "white"
            if self.buffer.buffer[i] != 0:
                cell_color = "lightblue"
            self.buffer_canvas.create_rectangle(cell_x1, cell_y1, cell_x2, cell_y2, fill=cell_color)
            if self.buffer.buffer[i] != 0:
                text = str(self.buffer.buffer[i])
                text_x = (cell_x1 + cell_x2) // 2
                text_y = (cell_y1 + cell_y2) // 2
                label = tk.Label(self.buffer_canvas, text=text, font=("TkDefaultFont", font_size))
                label.place(x=text_x, y=text_y, anchor="center")

    def change_buffer_size(self, size):
        # Clear the numbers
        for widget in self.buffer_canvas.winfo_children():
            widget.destroy()

        self.buffer_size.set(int(size))
        self.buffer = Buffer(size=self.buffer_size.get())
        for p in self.producers:
            p.buffer = self.buffer
        for c in self.consumers:
            c.buffer = self.buffer

    def update_gui(self):
        # Update buffer visualization
        self.draw_buffer()

        # Update position labels
        self.producer_label.config(text="Producer Position: %d" % self.buffer.get_producer_pos(), fg="green")
        self.consumer_label.config(text="Consumer Position: %d" % self.buffer.get_consumer_pos(), fg="red")

        # Schedule the next update
        self.after(100, self.update_gui)


class Console(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.text = tk.Text(self, state='disabled')
        self.text.pack(fill='both', expand=True)
        self.text.tag_config('stderr', foreground='red')
        self.text.tag_config('stdout', foreground='blue')
        self.queue = []

        # redirect stdout and stderr to the text widget
        sys.stdout = self
        sys.stderr = self

    def write(self, message):
        self.queue.append(message)
        self.display_queue()

    def display_queue(self):
        while self.queue:
            message = self.queue.pop(0)
            if message == '\n':
                self.text.insert('end', message)
                continue
            if 'Error' in message:
                self.text.tag_add('stderr', 'end-1c', 'end')
            else:
                self.text.tag_add('stdout', 'end-1c', 'end')
            self.text.configure(state='normal')
            self.text.insert('end', message)
            self.text.configure(state='disabled')
            self.text.see('end')


if __name__ == "__main__":
    root = tk.Tk()
    app = Application(master=root)
    console = Console(root)
    console.pack(side='bottom', fill='both', expand=True)

    # Create some producer and consumer threads
    for i in range(3):
        p = Producer(app.buffer, i)
        c = Consumer(app.buffer, i)
        app.producers.append(p)
        app.consumers.append(c)
        p.start()
        c.start()

    app.mainloop()

