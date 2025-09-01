# LarpManager - https://larpmanager.com
#
# This file is part of LarpManager and is dual-licensed:
#
# 1. Under the terms of the GNU Affero General Public License (AGPL) version 3,
#    as published by the Free Software Foundation. You may use, modify, and
#    distribute this file under those terms.
#
# 2. Under a commercial license, allowing use in closed-source or proprietary
#    environments without the obligations of the AGPL.
#
# If you have obtained this file under the AGPL, and you make it available over
# a network, you must also make the complete source code available under the same license.
#
# For more information or to purchase a commercial license, contact:
# commercial@larpmanager.com
#
# SPDX-License-Identifier: AGPL-3.0-or-later OR Proprietary

from django import forms
from django.utils.translation import gettext_lazy as _

from larpmanager.forms.base import MyForm
from larpmanager.models.characterinventory import CharacterInventory, PoolType, PoolBalance
from larpmanager.models.event import Event
from larpmanager.models.writing import Character


class CharacterInventoryBaseForm(MyForm):
    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class OrgaCharacterInventoryForm(CharacterInventoryBaseForm, forms.ModelForm):
    ##load_js = ["characters-choices"]

    page_title = _("Inventories")

    page_info = _("This page allows you to add or edit a character inventory")

    owners = forms.ModelMultipleChoiceField(
        queryset=Character.objects.all(),
        required=False,
        widget=forms.SelectMultiple
    )

    class Meta:
        model = CharacterInventory
        fields = ["name", "number", "event", "owners"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["owners"] = forms.MultipleChoiceField(
            label=_("Owners"),
            required=False,
            choices=[(c.id, str(c)) for c in self.params["event"].get_elements(Character)],
            widget=forms.SelectMultiple(attrs={"class": "form-control"}),
        )

    def save(self, commit=True):
        ci = CharacterInventory(
            name=self.cleaned_data["name"],
            number=self.cleaned_data["number"],
            event=Event.objects.get(id=self.cleaned_data["event"]),
        )
        ci.save()
        ci.owners.set(Character.objects.filter(id__in=self.cleaned_data["owners"]))

        # Automatically create one PoolBalance for every PoolType
        for pt in PoolType.objects.all():
            PoolBalance.objects.create(inventory=ci, pool_type=pt, amount=0)

        return ci