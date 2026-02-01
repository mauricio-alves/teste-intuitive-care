FROM postgres:14-bookworm

RUN localedef -i pt_BR -c -f UTF-8 -A /usr/share/locale/locale.alias pt_BR.UTF-8
ENV LANG pt_BR.utf8

RUN mkdir -p /scripts /data /input_t1 /input_t2_out /input_t2_temp

EXPOSE 5432