import matplotlib.pyplot as plt

def black(df, dir, name):
	fig, ax = plt.subplots(figsize=(10, 6))
	ax.set_facecolor('black')

	ax.plot(df['lon'], df['lat'], color='white', linewidth=1)
	ax.set_aspect('equal', 'datalim')
	ax.set_xticks([], [])
	ax.set_yticks([], [])
	ax.tick_params(axis='both', which='both', bottom=False, top=False, left=False, right=False)
	ax.autoscale()

	fig.tight_layout(pad=0, w_pad=0, h_pad=0)
 
	plt.savefig(
		f"{dir}/{name}.png", 
		dpi=300, 
		facecolor=fig.get_facecolor(), 
		edgecolor='none',
	)