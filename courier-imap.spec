%define name	courier-imap
%define version 4.3.0
%define release %mkrel 4

Name:		%{name}
Version:	%{version}
Release:	%{release}
Summary:	IMAP server that uses Maildirs
License:	GPL
Group:		System/Servers
URL:		http://www.courier-mta.org
Source0:	http://prdownloads.sourceforge.net/courier/%{name}-%{version}.tar.bz2
Source1:	%{name}.imapd-init
Source2:	%{name}.imapd-ssl-init
Source3:	%{name}.pop3d-init
Source4:	%{name}.pop3d-ssl-init
Patch0:		courier-imap-4.1.1-pam_service_name.diff
Requires:	courier-base = %{version}
Requires:	courier-authdaemon
Requires(pre):	rpm-helper >= 0.21
Requires(post):	rpm-helper >= 0.19
Requires(preun):	rpm-helper >= 0.19
Requires(postun):	rpm-helper >= 0.19
BuildRequires:	gdbm-devel
BuildRequires:	openssl-devel
BuildRequires:	courier-authlib-devel
BuildRequires:	courier-authdaemon
BuildRequires:	rpm-helper >= 0.21
BuildRoot:	%{_tmppath}/%{name}-%{version}

%description
Courier-IMAP is an IMAP server for Maildir mailboxes. This package contains
the standalone version of the IMAP server that's included in the Courier
mail server package. This package is a standalone version for use with
other mail servers. Do not install this package if you intend to install
the full Courier mail server.  Install the Courier package instead.

%package -n courier-base
Summary:	Courier base files for POP and IMAP servers
Group:		System/Servers
Obsoletes:	maildirmake++

%description -n courier-base
This package contains the base files for POP and IMAP servers.

%package -n courier-pop
Summary:	Courier POP servers
Group:		System/Servers
Requires:	courier-base = %{version}
Requires:	courier-authdaemon
Requires(pre):	rpm-helper

%description -n courier-pop
This package contains the POP servers of the Courier-IMAP
server suite.

%prep
%setup -q
%patch0 -p1
chmod 644 maildir/README.sharedfolders.html imap/README.html


%build
%serverbuild
%configure2_5x \
    --enable-unicode \
    --libexec=%{_libdir}/%{name} \
    --datadir=%{_datadir}/%{name} \
    --sysconfdir=%{_sysconfdir}/courier

%make

%check
%{__make} check

%install
rm -rf %{buildroot}
install -d -m 755 %{buildroot}%{_initrddir}
install -d -m 755 %{buildroot}%{_sysconfdir}/pam.d
%makeinstall_std

# delete upstream init scripts and install custom one
rm -f  %{buildroot}%{_libdir}/%{name}/*.rc
install -m 755 %{SOURCE1} %{buildroot}%{_initrddir}/courier-imapd
install -m 755 %{SOURCE2} %{buildroot}%{_initrddir}/courier-imapd-ssl
install -m 755 %{SOURCE3} %{buildroot}%{_initrddir}/courier-pop3d
install -m 755 %{SOURCE4} %{buildroot}%{_initrddir}/courier-pop3d-ssl
perl -pi -e 's|\@libdir\@|%{_libdir}|' %{buildroot}%{_initrddir}/*

# fix configuration
for file in %{buildroot}%{_sysconfdir}/courier/*.dist; do
    mv $file  %{buildroot}%{_sysconfdir}/courier/`basename $file .dist`
done
chmod 644 %{buildroot}%{_sysconfdir}/courier/imapd*
chmod 644 %{buildroot}%{_sysconfdir}/courier/pop3d*

# fix pam configuration
rm -f %{buildroot}%{_sysconfdir}/pam.d/*
cat > %{buildroot}%{_sysconfdir}/pam.d/courier-imap <<EOF
auth	required	pam_nologin.so
auth	include	system-auth
account	include	system-auth
session	include	system-auth
EOF
cat > %{buildroot}%{_sysconfdir}/pam.d/courier-pop3 <<EOF
auth	required	pam_nologin.so
auth	include	system-auth
account	include	system-auth
session	include	system-auth
EOF

# fix name conflict for doc files
cp imap/README imap/README.imap
cp rfc822/ChangeLog rfc822/ChangeLog.rfc822
cp unicode/README unicode/README.unicode

# Maildir
install -d -m 755 %{buildroot}%{_sysconfdir}/skel
(cd %{buildroot}%{_sysconfdir}/skel && %{buildroot}%{_bindir}/maildirmake Maildir)


cat > README.mdv << EOF
Mandriva RPM specific notes

Upgrade
-------
Upstream upgrade procedure consists of shipping new configuration files with
.dist suffix, then running sysconftool script to merge with current
configuration. This packages ships new configuration files with their final
name instead, wich will be saved by rpm as .rpmnew if original ones have been
modified, and run sysconftools script during upgrade automatically.

Init scripts
------------
Upstream init system consist of one unique init script, using values in
configuration files to select wich services to run. This package ships a
replacement init system, composed of four distincts standard services script
for each server, so as to use normal procedure (chkconfig command) to determine
which one to run. As a side-effect, the various *START variables in
configuration files have no effect.
EOF

# replace SSL certs configuration with our own
rm -f %{buildroot}%{_sysconfdir}/courier/imapd.cnf
rm -f %{buildroot}%{_sysconfdir}/courier/pop3d.cnf
perl -pi \
    -e 's|TLS_CERTFILE=.*|TLS_CERTFILE=%{_sysconfdir}/pki/tls/private/courier-imap.pem|'\
    %{buildroot}%{_sysconfdir}/courier/imapd-ssl
perl -pi \
    -e 's|TLS_CERTFILE=.*|TLS_CERTFILE=%{_sysconfdir}/pki/tls/private/courier-pop.pem|'\
    %{buildroot}%{_sysconfdir}/courier/pop3d-ssl

%post
if [ -f %{_sysconfdir}/courier/imapd.rpmnew ]; then
    %{_libdir}/courier-authlib/sysconftool %{_sysconfdir}/courier/imapd.rpmnew >/dev/null
fi
if [ -f %{_sysconfdir}/courier/imapd-ssl.rpmnew ]; then
    %{_libdir}/courier-authlib/sysconftool %{_sysconfdir}/courier/imapd-ssl.rpmnew >/dev/null
fi
%_post_service courier-imapd
%_post_service courier-imapd-ssl
%_create_ssl_certificate courier-imap -b

%preun 
%_preun_service courier-imapd
%_preun_service courier-imapd-ssl

%post -n courier-pop
%_create_ssl_certificate courier-pop -b
if [ -f %{_sysconfdir}/courier/pop3d.rpmnew ]; then
    %{_libdir}/courier-authlib/sysconftool %{_sysconfdir}/courier/pop3d.rpmnew >/dev/null
fi
if [ -f %{_sysconfdir}/courier/pop3d-ssl.rpmnew ]; then
    %{_libdir}/courier-authlib/sysconftool %{_sysconfdir}/courier/pop3d-ssl.rpmnew >/dev/null
fi
%_post_service courier-pop3d
%_post_service courier-pop3d-ssl

%preun -n courier-pop
%_preun_service courier-pop3d
%_preun_service courier-pop3d-ssl

%clean
rm -rf %{buildroot}

%files -n courier-base
%defattr(-,root,root)
%doc INSTALL INSTALL.html NEWS README README.mdv
%doc liblock/*.html
%doc maildir/README.* maildir/*.html
%doc rfc2045/*.html
%doc rfc822/ChangeLog.rfc822 rfc822/rfc822.html
%doc tcpd/README.* tcpd/*.html
%doc unicode/README.*
%doc maildir/maildirmake.html
%config(noreplace) %{_sysconfdir}/courier/quotawarnmsg.example
%config(noreplace) %{_sysconfdir}/courier/shared
%config(noreplace) %{_sysconfdir}/courier/shared.tmp
%config(noreplace) %{_sysconfdir}/skel/Maildir
%{_bindir}/maildirmake
%{_bindir}/deliverquota
%{_bindir}/couriertls
%{_bindir}/maildirkw
%{_bindir}/maildiracl
%{_sbindir}/sharedindexinstall
%{_sbindir}/sharedindexsplit
%{_mandir}/man1/maildirmake.1*
%{_mandir}/man1/couriertcpd.1*
%{_mandir}/man1/maildiracl.1*
%{_mandir}/man1/maildirkw.1*
%{_mandir}/man8/deliverquota.8*
%{_libdir}/%{name}

%files
%defattr(-,root,root)
%doc imap/BUGS imap/ChangeLog imap/README.* imap/*.html
%config(noreplace) %{_sysconfdir}/pam.d/courier-imap
%config(noreplace) %{_sysconfdir}/courier/imapd
%config(noreplace) %{_sysconfdir}/courier/imapd-ssl
%{_initrddir}/courier-imapd
%{_initrddir}/courier-imapd-ssl
%{_bindir}/imapd
%{_sbindir}/imaplogin
%{_sbindir}/mkimapdcert
%{_mandir}/man8/imapd.8*
%{_mandir}/man8/mkimapdcert.8*
%{_datadir}/%{name}/mkimapdcert

%files -n courier-pop
%defattr(-,root,root)
%config(noreplace) %{_sysconfdir}/pam.d/courier-pop3
%config(noreplace) %{_sysconfdir}/courier/pop3d
%config(noreplace) %{_sysconfdir}/courier/pop3d-ssl
%{_initrddir}/courier-pop3d
%{_initrddir}/courier-pop3d-ssl
%{_bindir}/pop3d
%{_sbindir}/pop3login
%{_sbindir}/mkpop3dcert
%{_mandir}/man8/mkpop3dcert.8*
%{_datadir}/%{name}/mkpop3dcert


