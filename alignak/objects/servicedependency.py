#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2015: Alignak team, see AUTHORS.txt file for contributors
#
# This file is part of Alignak.
#
# Alignak is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Alignak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Alignak.  If not, see <http://www.gnu.org/licenses/>.
#
#
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Guillaume Bour, guillaume@bour.cc
#     Arthur Gautier, superbaloo@superbaloo.net
#     aviau, alexandre.viau@savoirfairelinux.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Grégory Starck, g.starck@gmail.com
#     Alexander Springer, alex.spri@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Christophe Simon, geektophe@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Romain Forlot, rforlot@yahoo.com
#     Romain THERRAT, romain42@gmail.com

#  This file is part of Shinken.
#
#  Shinken is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Shinken is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with Shinken.  If not, see <http://www.gnu.org/licenses/>.
"""This module provides Servicedependency and Servicedependencies classes that
implements dependencies between services. Basically used for parsing.

"""
from alignak.property import BoolProp, StringProp, ListProp
from alignak.log import logger

from .item import Item, Items


class Servicedependency(Item):
    """Servicedependency class is a simple implementation of service dependency as
    defined in a monitoring context (dependency period, notification_failure_criteria ..)

    """
    _id = 0
    my_type = "servicedependency"

    # F is dep of D
    # host_name                      Host B
    #       service_description             Service D
    #       dependent_host_name             Host C
    #       dependent_service_description   Service F
    #       execution_failure_criteria      o
    #       notification_failure_criteria   w,u
    #       inherits_parent         1
    #       dependency_period       24x7

    properties = Item.properties.copy()
    properties.update({
        'dependent_host_name':           StringProp(),
        'dependent_hostgroup_name':      StringProp(default=''),
        'dependent_service_description': StringProp(),
        'host_name':                     StringProp(),
        'hostgroup_name':                StringProp(default=''),
        'service_description':           StringProp(),
        'inherits_parent':               BoolProp(default=False),
        'execution_failure_criteria':    ListProp(default=['n'], split_on_coma=True),
        'notification_failure_criteria': ListProp(default=['n'], split_on_coma=True),
        'dependency_period':             StringProp(default=''),
        'explode_hostgroup':             BoolProp(default=False)
    })

    def get_name(self):
        """Get name based on 4 class attributes
        Each attribute is substituted by '' if attribute does not exist

        :return: dependent_host_name/dependent_service_description..host_name/service_description
        :rtype: str
        TODO: Clean this function (use format for string)
        """
        return getattr(self, 'dependent_host_name', '') + '/'\
            + getattr(self, 'dependent_service_description', '') \
            + '..' + getattr(self, 'host_name', '') + '/' \
            + getattr(self, 'service_description', '')


class Servicedependencies(Items):
    """Servicedependencies manage a list of Servicedependency objects, used for parsing configuration

    """
    inner_class = Servicedependency  # use for know what is in items

    def delete_servicesdep_by_id(self, ids):
        """Delete a list of servicedependency

        :param ids: ids list to delete
        :type ids: list
        :return: None
        """
        for s_id in ids:
            del self[s_id]

    def add_service_dependency(self, dep_host_name, dep_service_description,
                               par_host_name, par_service_description):
        """Instantiate and add a Servicedependency object to the items dict::

        * notification criteria is "u,c,w"
        * inherits_parent is True

        :param dep_host_name: dependent host name
        :type dep_host_name: str
        :param dep_service_description: dependent service description
        :type dep_service_description: str
        :param par_host_name: host name
        :type par_host_name: str
        :param par_service_description: service description
        :type par_service_description: str
        :return: None
        """
        # We create a "standard" service_dep
        prop = {
            'dependent_host_name':           dep_host_name,
            'dependent_service_description': dep_service_description,
            'host_name':                     par_host_name,
            'service_description':           par_service_description,
            'notification_failure_criteria': 'u,c,w',
            'inherits_parent': '1',
        }
        sd = Servicedependency(prop)
        self.add_item(sd)

    def explode_hostgroup(self, sd, hostgroups):
        """Explode a service dependency for each member of hostgroup

        :param sd: service dependency to explode
        :type sd: alignak.objects.servicedependency.Servicedependency
        :param hostgroups: used to find hostgroup objects
        :type hostgroups: alignak.objects.hostgroup.Hostgroups
        :return:None
        """
        # We will create a service dependency for each host part of the host group

        # First get services
        snames = [d.strip() for d in sd.service_description.split(',')]

        # And dep services
        dep_snames = [d.strip() for d in sd.dependent_service_description.split(',')]

        # Now for each host into hostgroup we will create a service dependency object
        hg_names = [n.strip() for n in sd.hostgroup_name.split(',')]
        for hg_name in hg_names:
            hg = hostgroups.find_by_name(hg_name)
            if hg is None:
                err = "ERROR: the servicedependecy got an unknown hostgroup_name '%s'" % hg_name
                self.configuration_errors.append(err)
                continue
            hnames = []
            hnames.extend([m.strip() for m in hg.members])
            for hname in hnames:
                for dep_sname in dep_snames:
                    for sname in snames:
                        new_sd = sd.copy()
                        new_sd.host_name = hname
                        new_sd.service_description = sname
                        new_sd.dependent_host_name = hname
                        new_sd.dependent_service_description = dep_sname
                        self.add_item(new_sd)

    def explode(self, hostgroups):
        """Explode all service dependency for each member of hostgroups
        Each member of dependent hostgroup or hostgroup in dependency have to get a copy of
        service dependencies (quite complex to parse)

        :param hostgroups: used to look for hostgroup
        :type hostgroups: alignak.objects.hostgroup.Hostgroups
        :return: None
        """
        # The "old" services will be removed. All services with
        # more than one host or a host group will be in it
        srvdep_to_remove = []

        # Then for every host create a copy of the service with just the host
        # because we are adding services, we can't just loop in it
        servicedeps = self.items.keys()
        for s_id in servicedeps:
            sd = self.items[s_id]
            # Have we to explode the hostgroup into many service?
            if bool(getattr(sd, 'explode_hostgroup', 0)) and \
               hasattr(sd, 'hostgroup_name'):
                self.explode_hostgroup(sd, hostgroups)
                srvdep_to_remove.append(s_id)
                continue

            # Get the list of all FATHER hosts and service deps
            hnames = []
            if hasattr(sd, 'hostgroup_name'):
                hg_names = [n.strip() for n in sd.hostgroup_name.split(',')]
                hg_names = [hg_name.strip() for hg_name in hg_names]
                for hg_name in hg_names:
                    hg = hostgroups.find_by_name(hg_name)
                    if hg is None:
                        err = "ERROR: the servicedependecy got an" \
                              " unknown hostgroup_name '%s'" % hg_name
                        hg.configuration_errors.append(err)
                        continue
                    hnames.extend([m.strip() for m in hg.members])

            if not hasattr(sd, 'host_name'):
                sd.host_name = ''

            if sd.host_name != '':
                hnames.extend([n.strip() for n in sd.host_name.split(',')])
            snames = [d.strip() for d in sd.service_description.split(',')]
            couples = []
            for hname in hnames:
                for sname in snames:
                    couples.append((hname.strip(), sname.strip()))

            if not hasattr(sd, 'dependent_hostgroup_name') and hasattr(sd, 'hostgroup_name'):
                sd.dependent_hostgroup_name = sd.hostgroup_name

            # Now the dep part (the sons)
            dep_hnames = []
            if hasattr(sd, 'dependent_hostgroup_name'):
                hg_names = [n.strip() for n in sd.dependent_hostgroup_name.split(',')]
                hg_names = [hg_name.strip() for hg_name in hg_names]
                for hg_name in hg_names:
                    hg = hostgroups.find_by_name(hg_name)
                    if hg is None:
                        err = "ERROR: the servicedependecy got an " \
                              "unknown dependent_hostgroup_name '%s'" % hg_name
                        hg.configuration_errors.append(err)
                        continue
                    dep_hnames.extend([m.strip() for m in hg.members])

            if not hasattr(sd, 'dependent_host_name'):
                sd.dependent_host_name = getattr(sd, 'host_name', '')

            if sd.dependent_host_name != '':
                dep_hnames.extend([n.strip() for n in sd.dependent_host_name.split(',')])
            dep_snames = [d.strip() for d in sd.dependent_service_description.split(',')]
            dep_couples = []
            for dep_hname in dep_hnames:
                for dep_sname in dep_snames:
                    dep_couples.append((dep_hname.strip(), dep_sname.strip()))

            # Create the new service deps from all of this.
            for (dep_hname, dep_sname) in dep_couples:  # the sons, like HTTP
                for (hname, sname) in couples:  # the fathers, like MySQL
                    new_sd = sd.copy()
                    new_sd.host_name = hname
                    new_sd.service_description = sname
                    new_sd.dependent_host_name = dep_hname
                    new_sd.dependent_service_description = dep_sname
                    self.add_item(new_sd)
                # Ok so we can remove the old one
                srvdep_to_remove.append(s_id)

        self.delete_servicesdep_by_id(srvdep_to_remove)

    def linkify(self, hosts, services, timeperiods):
        """Create link between objects::

         * servicedependency -> host
         * servicedependency -> service
         * servicedependency -> timeperiods

        :param hosts: hosts to link
        :type hosts: alignak.objects.host.Hosts
        :param services: services to link
        :type services: alignak.objects.service.Services
        :param timeperiods: timeperiods to link
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :return: None
        """
        self.linkify_sd_by_s(hosts, services)
        self.linkify_sd_by_tp(timeperiods)
        self.linkify_s_by_sd()

    def linkify_sd_by_s(self, hosts, services):
        """Replace dependent_service_description and service_description
        in service dependency by the real object

        :param hosts: host list, used to look for a specific one
        :type hosts: alignak.objects.host.Hosts
        :param services: service list to look for a specific one
        :type services: alignak.objects.service.Services
        :return: None
        """
        to_del = []
        errors = self.configuration_errors
        warns = self.configuration_warnings
        for sd in self:
            try:
                s_name = sd.dependent_service_description
                hst_name = sd.dependent_host_name

                # The new member list, in id
                s = services.find_srv_by_name_and_hostname(hst_name, s_name)
                if s is None:
                    host = hosts.find_by_name(hst_name)
                    if not (host and host.is_excluded_for_sdesc(s_name)):
                        errors.append("Service %s not found for host %s" % (s_name, hst_name))
                    elif host:
                        warns.append("Service %s is excluded from host %s ; "
                                     "removing this servicedependency as it's unusuable."
                                     % (s_name, hst_name))
                    to_del.append(sd)
                    continue
                sd.dependent_service_description = s

                s_name = sd.service_description
                hst_name = sd.host_name

                # The new member list, in id
                s = services.find_srv_by_name_and_hostname(hst_name, s_name)
                if s is None:
                    host = hosts.find_by_name(hst_name)
                    if not (host and host.is_excluded_for_sdesc(s_name)):
                        errors.append("Service %s not found for host %s" % (s_name, hst_name))
                    elif host:
                        warns.append("Service %s is excluded from host %s ; "
                                     "removing this servicedependency as it's unusuable."
                                     % (s_name, hst_name))
                    to_del.append(sd)
                    continue
                sd.service_description = s

            except AttributeError as err:
                logger.error("[servicedependency] fail to linkify by service %s: %s", sd, err)
                to_del.append(sd)

        for sd in to_del:
            self.remove_item(sd)

    def linkify_sd_by_tp(self, timeperiods):
        """Replace dependency_period by a real object in service dependency

        :param timeperiods: list of timeperiod, used to look for a specific one
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :return: None
        """
        for sd in self:
            try:
                tp_name = sd.dependency_period
                tp = timeperiods.find_by_name(tp_name)
                sd.dependency_period = tp
            except AttributeError, exp:
                logger.error("[servicedependency] fail to linkify by timeperiods: %s", exp)

    def linkify_s_by_sd(self):
        """Add dependency in service objects

        :return: None
        """
        for sd in self:
            dsc = sd.dependent_service_description
            sdval = sd.service_description
            if dsc is not None and sdval is not None:
                dp = getattr(sd, 'dependency_period', None)
                dsc.add_service_act_dependency(sdval, sd.notification_failure_criteria,
                                               dp, sd.inherits_parent)
                dsc.add_service_chk_dependency(sdval, sd.execution_failure_criteria,
                                               dp, sd.inherits_parent)

    def is_correct(self):
        """Check if this host configuration is correct ::

        * All required parameter are specified
        * Go through all configuration warnings and errors that could have been raised earlier

        :return: True if the configuration is correct, otherwise False
        :rtype: bool
        """
        r = super(Servicedependencies, self).is_correct()
        return r and self.no_loop_in_parents("service_description", "dependent_service_description")