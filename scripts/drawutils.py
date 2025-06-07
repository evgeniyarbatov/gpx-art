import matplotlib.pyplot as plt
import random

def color(df, dir, name):
    # Define some visually appealing color pairs (background, line)
    color_pairs = [
        ('#1a1a1a', '#00ffcc'),
        ('#f5f5f5', '#ff3366'),
        ('#002b36', '#268bd2'),
        ('#ffffff', '#ff9900'),
        ('#2c3e50', '#e74c3c'),
        ('#ffefd5', '#4682b4'),
        ('#0f0f0f', '#39ff14'),
        ('#fffbf0', '#8e44ad'),
        ('#1e272e', '#34ace0'),
        ('#fafafa', '#e67e22'),
    ]

    # Choose a random color pair
    bg_color, line_color = random.choice(color_pairs)

    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    ax.set_facecolor(bg_color)

    ax.plot(df['lon'], df['lat'], color=line_color, linewidth=5)
    ax.set_aspect('equal', 'datalim')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.tick_params(axis='both', which='both', bottom=False, top=False, left=False, right=False)
    ax.autoscale()

    fig.tight_layout(pad=0, w_pad=0, h_pad=0)

    plt.savefig(
        f"{dir}/{name}-color-plot.png",
        dpi=300,
        facecolor=fig.get_facecolor(),
        edgecolor='none',
    )
