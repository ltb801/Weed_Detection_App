import rasterio
import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt


# Function to plot GeoTIFF and capture points
def plot_and_capture_points(tif_path, scale):
    with rasterio.open(tif_path) as src:
        # Read the data at a lower resolution
        low_res_data = src.read(1, out_shape=(src.height // scale, src.width // scale))
        transform = src.transform  # Original full-resolution transform

        fig, ax = plt.subplots(1, 1, figsize=(10, 10))
        ax.imshow(low_res_data, cmap='gray', interpolation='nearest')  # Using a grayscale colormap
        ax.set_title('Click to select boundary points; close the window when done')
        points = []
        line, = ax.plot([], [], 'r-')  # Initialize a line object

        def onclick(event):
            if event.inaxes is not ax:
                return  # Ignore clicks outside the axes
            # Calculate the original resolution coordinates from the clicked position
            original_x = int(event.xdata * scale)
            original_y = int(event.ydata * scale)
            # Convert pixel coordinates to geographic coordinates using original transform
            lon, lat = transform * (original_x, original_y)
            print(f'Geo-coordinates: Longitude: {lon}, Latitude: {lat}')
            points.append((lon, lat))
            ax.plot(event.xdata, event.ydata, 'ro')  # Plot point on the scaled image

            # Update line data
            xdata, ydata = line.get_data()
            xdata = list(xdata) + [event.xdata]
            ydata = list(ydata) + [event.ydata]
            line.set_data(xdata, ydata)
            fig.canvas.draw()

        cid = fig.canvas.mpl_connect('button_press_event', onclick)
        plt.show()

        return points
