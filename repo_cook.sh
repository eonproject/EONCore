#!/bin/bash
#### config section
patch_dir=../git-export/patches
authors=(
    "gnufoo <xia.tony@gmail.com>"
#    "captionkirk <captionkirk@outlook.com>"
#    "heypat <patrickhedy@hotmail.com>"
#    "Sam-Lucius <sa.luci@hotmail.com>"
#    "TyroneFrancis <tyrone.fran@hotmail.com>"
#    "Eugene Raymond <eug.ray@hotmail.com>"
)
author_serial_max=5
# in iso-8601 format
first_commit_date="2018-03-10T07:12:31+08:00"
last_commit_date="2018-08-10T16:03:06+08:00"

##
function date2ts(){
    date --date "${1}" "+%s"
}

function ts2date(){
    date -R --date "@${1}"
}
## 
patch_first_ts=`ls ${patch_dir} | head -n 1 | xargs -I{} head ${patch_dir}/{} | grep 'Date: ' | sed 's/Date: //' | xargs -I{} date --date "{}" "+%s"`
patch_last_ts=`ls ${patch_dir} | tail -n 1 | xargs -I{} head ${patch_dir}/{} | grep 'Date: ' | sed 's/Date: //' | xargs -I{} date --date "{}" "+%s"`

ori_ts_base=$patch_first_ts
ori_ts_range=`expr $patch_last_ts - $patch_first_ts`

commit_ts_base=`date2ts ${first_commit_date}`
commit_ts_range=$((`date2ts ${last_commit_date}` - $commit_ts_base))
commit_offset_scale=`echo "scale=10;$commit_ts_range/$ori_ts_range" | bc`

function replace_date(){
    offset=$((`date2ts "${1}"` - $ori_ts_base))
    ts=`echo "scale=0;$commit_ts_base + $offset * $commit_offset_scale" | bc`
    ts2date $ts
}

##
function replace_author() {
    current_author=$1
    current_count=$2
    if (( ${current_count} > 0 ))
    then
        current_count=$((${current_count} - 1))
        echo "${current_author}"
    else
        current_count=$((${RANDOM} % ${author_serial_max}))
        current_author_idx=$((${RANDOM} % ${#authors[@]}))
        current_author="${authors[current_author_idx]}"
        echo "${current_author}"
    fi
    exit ${current_count}
}

#### apply all patches with expected author/date
git init
cauthor=''
cauthor_cnt=0
for pf in `ls ${patch_dir}`
do
    ccommit=`head -n 1 ${patch_dir}/${pf} | awk '{print $2}'`
    cdate=`head ${patch_dir}/${pf} | grep 'Date: ' | sed 's/Date: //'`
    # cauthor=`head ${patch_dir}/${pf} | grep 'From: ' | sed 's/From: //'`
    ctitle=`head -n20 ${patch_dir}/${pf} | sed '/---/q' | sed '/MIME-Version/'q | sed -n '/Subject/, $'p | sed '/MIME-Version/'d | sed -e 's/^---$//g' | sed '/^$/d'  | sed -E 's/Subject: \[PATCH( [0-9]+\/[0-9]+)?\] //' | sed -E ':a ; $!N ; s/\n\s+/ / ; ta ; P ; D' | perl -CS -MEncode -ne 'print decode("MIME-Header", $_)'`
    ccontent=`cat ${patch_dir}/${pf} | sed '/---/q' | sed -n '/Content-Transfer-Encoding/,$p' | sed -n '2, $'p | sed -e 's/^---$//g' | sed '/^$/d' | sed -E 's/\(\@[^\)]*\)//g'`
    # echo $pf ": " $cdate " " $cauthor " " $ctitle
    ## reset author / date
    cauthor=`replace_author "${cauthor}" "${cauthor_cnt}"`
    cauthor_cnt=$?
    cdate=`replace_date "${cdate}"`
    cusername=`echo "$cauthor" | awk -F"<" '{print $1}'`
    cuseremail=`echo "$cauthor" | awk -F"<" '{print $2}' | sed -e 's/>//'`
    ## apply & commit
    echo "-------apply commit: $ccommit of $pf"
    echo " author: $cauthor"
    echo " date: $cdate"
    echo " subject: $ctitle"
    echo " description: $ccontent"
    echo " user.name: $cusername"
    echo " user.email: $cuseremail"

    git apply ${patch_dir}/${pf}
    git add .
    export GIT_COMMITTER_DATE="$cdate"
    git -c "user.name=${cusername}" -c "user.email=${cuseremail}" commit --author "$cauthor" --date "$cdate" -m "$ctitle" -m "$ccontent"

done
