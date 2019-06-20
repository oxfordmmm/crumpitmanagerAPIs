python3 /mnt/nanostore/soft/print_old_runs.py > /tmp/delete_runs.txt

while read loc; do
    echo ${loc}
    cd $loc
    nextflow clean -f
    nextflow clean -f
    nextflow clean -f
    rm -r fastqs mpileup
#    rm -r sorted
    echo "done"  ${loc}
done < /tmp/delete_runs.txt
