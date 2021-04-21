import os
import subprocess as sp

import pandas as pd
import seaborn as sns
import matplotlib
import matplotlib.pyplot as plt


class plot_depth_by_barcode:
    def run(run, ref_name, ref_path, fq_path, sing_img, out_dir):
        '''
        Plot log-scaled depth for each barcode with reads mapping to the reference
        Author: Bede Constantinides (modified by Jez Swann)
        Conda: conda create -n depthplots python=3 pandas matplotlib seaborn minimap2 samtools
        '''
        os.makedirs(f'{out_dir}/tmp', exist_ok=True)

        fq_fns = [fn for fn in os.listdir(fq_path) if 'barcode' in fn]
        barcodes = sorted({fn.partition('_')[0].replace('barcode','') for fn in fq_fns})
        barcodes_fq_fns = {bc: [f'{fq_path}/{fn}'
                            for fn in fq_fns if fn.startswith(f'barcode{bc}')]
                            for bc in barcodes}
        cmds = []
        for barcode, fns in barcodes_fq_fns.items():
            cmds.append(f"singularity exec {sing_img} /bin/bash -c \" "
                        f"cat {' '.join(fns)}"
                        f" | minimap2 -ax asm20 -t6 {ref_path} -"
                        f" | samtools view -uF 4"
                        f" | samtools sort -"
                        f" | samtools depth -aa -m 1000000 - > {out_dir}/tmp/barcode{barcode}.depth \"")

        runs = [sp.run(cmd, shell=True, check=False, stdout=sp.PIPE, stderr=sp.PIPE) for cmd in cmds]

        # Parse depths
        depth_dfs = []
        depth_fns = [fn for fn in os.listdir(f'{out_dir}/tmp/') if fn.endswith('.depth')]
        barcodes = sorted({fn.partition('.')[0].replace('barcode','') for fn in depth_fns})
        for barcode in barcodes:
            depth_df = pd.read_csv(f'{out_dir}/tmp/barcode{barcode}.depth',
                                sep='\t', header=None, usecols=(1,2), names=('pos', 'depth'))
            depth_df = depth_df.assign(sample=f'barcode{barcode}')
            depth_df['depth'] = depth_df['depth'].astype(int)
            depth_dfs.append(depth_df)
        depth_df = pd.concat(depth_dfs)

        # Plot
        sns.set_style('white')
        g = sns.FacetGrid(depth_df, col='sample', col_order=sorted(depth_df['sample'].unique()),
                        col_wrap=4, height=3, aspect=1.5)
        g.map(sns.lineplot, 'pos', 'depth')
        g.map(plt.axhline, y=1000, ls='--', c='green')
        g.map(plt.axhline, y=100, ls='--', c='green')
        g.map(plt.axhline, y=10, ls='--', c='red')
        g.set(ylabel='Read depth', xlabel='Reference position', yscale='log', ylim=(1, None))
        plt.tight_layout()
        plt.suptitle(f'Depth for run {run} with reference {ref_name}')
        plt.subplots_adjust(top=0.92)
        plt.savefig(f'{out_dir}/{run}-depth.png', dpi=200)
        return f'{out_dir}/{run}-depth.png'



