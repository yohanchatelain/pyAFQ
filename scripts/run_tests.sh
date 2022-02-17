#!/bin/bash

#SBATCH --array=1-30
#SBATCH --nodes=1
#SBATCH --time=24:0:0
#SBATCH --mail-user=yohan.chatelain@gmail.com
#SBATCH --mail-type=ALL
#SBATCH --output=logs/%x.%A.%a.out
#SBATCH --error=logs/%x.%A.%a.err
#SBATCH --ntasks=40

FUZZY_LEVEL=$1
MCA_MODE=$2
ROOT=/home/g/glatard/ychatel/scratch/pyAFQ/
TEST=pyAFQ/AFQ/tests
SIF=$ROOT/containers/pyafq-fuzzy-${FUZZY_LEVEL}*.sif
LOG=results/log.${FUZZY_LEVEL}.${MCA_MODE}.${SLURM_ARRAY_TASK_ID}

echo "FUZZY_LEVEL=${FUZZY_LEVEL}"
echo "MCA_MODE=${MCA_MODE}"
echo "ROOT=${ROOT}"
echo "TEST=${TEST}"
echo "SIF=${SIF}"

echo "singularity exec \
    --home $ROOT \
    --pwd $ROOT/$TEST \
    --env VFC_BACKENDS_FROM_FILE=$PWD/scripts/vfcbackends-${MCA_MODE}.txt \
    --env VFC_BACKENDS_LOGGER=False \
    -B $(realpath pyAFQ/):$(realpath pyAFQ/) \
    -B $(realpath .cache/templateflow/):$(realpath .cache/templateflow/) \
    -B $(realpath .dipy/):$(realpath .dipy/) \
    ${SIF} \
    pytest --disable-pytest-warnings --pyargs AFQ \
    -m "not nightly and not nightly_basic and not nightly_msmt_and_init and not nightly_custom and not nightly_anisotropic and not nightly_slr and not nightly_pft and not nightly_reco" --durations=0"


singularity exec \
    --home $ROOT \
    --pwd $ROOT/$TEST \
    --env VFC_BACKENDS_FROM_FILE=$PWD/scripts/vfcbackends-${MCA_MODE}.txt \
    --env VFC_BACKENDS_LOGGER=False \
    -B $(realpath pyAFQ/):$(realpath pyAFQ/) \
    -B $(realpath .cache/templateflow/):$(realpath .cache/templateflow/) \
    -B $(realpath .dipy/):$(realpath .dipy/) \
    ${SIF} \
    pytest --disable-pytest-warnings --pyargs AFQ \
    -m "not nightly and not nightly_basic and not nightly_msmt_and_init and not nightly_custom and not nightly_anisotropic and not nightly_slr and not nightly_pft and not nightly_reco" --durations=0 > ${LOG}
