
#runs="$(ls -trd */)"

#runs="UVA_CAVP_33/
#UVA_CAVP_35/
#UVA_CAVP_34/
#UVA_CAVP_32/
#rhb_20181023_01/"

#runs="bcg_boil_7/"

#runs="P_water_myco/"
#runs="PHE_208_209/"

#runs="bcg_boil_8/"

#runs="bcg_boil_9_ubb/
#bcg_boil_10_unt/"

#runs="brctb_clinical_ubb_1/"

#runs="RPB004_3/
#RPB004_2/
#Porton-POC-rep-SP/"

#runs="RHB_reseq_run2/"

#runs="Porton-under20-rep/
#Porton-neg-rep/
#Porton-30-35-rep-rep/"

#runs="flu_feret_2/
#flu_feret_1/
#RPB004_4/
#RHB_reseq_run3/
#bcg_boil_15_ubb_104/
#bcg_boil_15_ubb_103/
#bcg_boil_15_ubb_102/
#bcg_boil_15_ubb_101/
#bcg_boil_15_ubb_0/"
#runs="bcg_ubb_boil_16_105/"

#runs="RHB_reseq_run3/"

#runs="Flu_season_1/
#Flu_season_2/
#Flu_season_3/
#Flu_season_4/
#Flu_season_5/
#Flu_season_6/
#Flu_season_7/
#Flu_season_8/
#Flu_season_9/
#Flu_season_10/
#Flu_season_11/
#Flu_season_12/
#Flu_season_13/
#Flu_season_14/
#Flu_season_15/
#Flu_season_16/
#Flu_season_17/
#Flu_season_18/
#Flu_season_20/
#Flu_season_21/"

#runs="Flu_season_19/
#Flu_season_22/
#Flu_season_23/"

#runs="105F220190228/
#107X320190228/
#102F20190228/
#105FEC20190228/
#Flu_season_11/
#Flu_season_17/
#Flu_season_19/
#Flu_season_23/
#103V20190304/
#104V220190304/
#105V220190304/
#NEGFEC20190304/
#102V20190304/
#Flu_season_22/
#Flu_season_24/
#Flu_season_25/
#"

#runs="RHB_reseq_run3_6/
#RHB_reseq_run3_8/"

runs="Flu_season_30/
Flu_season_26/
Flu_season_27/
Flu_season_28/
Flu_season_29/"

runs="bcg_ubb_untr_19/
RHB_reseq_run4/
bcg_ubb_boil_18_101/
bcg_ubb_boil_18_102/
bcg_ubb_boil_18_103/
bcg_ubb_boil_18_104/
bcg_ubb_boil_18_105/
bcg_ubb_untr_21/
bcg_ubb_boil_20/"

#runs="mixedgc10/
#mixedgc9/
#mixedgc8/
#mixedgc7/
#mixedgc6/"

runs="RHB_APHA_T2_run1/
RHB_APHA_T2_run2/
porton-100k-high-ct/
porton-100k-low-ct/
Porton-23-27-reps/
"

runs="RHB_APHA_T2_run3/
RHB_APHA_T2_run4/"

runs="RPB004_10/
RPB004_9/
RPB004_8/
RPB004_7/"

runs="RPB004_12/
RPB004_13/"


for run in ${runs}
do
echo ${run}
ssh csana1 "mkdir /home/ndm.local/Nanopore/${run}" >> ${run}upload.out 2>> ${run}upload.log
rsync  -avP ${run}basecalled_fastq csana1:/home/ndm.local/Nanopore/${run} >> ${run}upload.out 2>> ${run}upload.log
rsync  -avP ${run}sequencing_summary.txt.gz csana1:/home/ndm.local/Nanopore/${run} >> ${run}upload.out 2>> ${run}upload.log
rsync  -avP ${run}f5s csana1:/home/ndm.local/Nanopore/${run} >> ${run}upload.out 2>> ${run}upload.log
#rm -r ${run}mpileup ${run}sorted
#rm -r ${run}fastqs
done


