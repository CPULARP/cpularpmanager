# LarpManager - https://larpmanager.com
# Copyright (C) 2025 Scanagatta Mauro
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

import traceback

from django import forms
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max
from django.forms import CharField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from larpmanager.forms.base import BaseRegistrationForm, MyForm
from larpmanager.forms.utils import EventCharacterS2Widget, EventCharacterS2WidgetMulti, WritingTinyMCE
from larpmanager.models.access import get_event_staffers
from larpmanager.models.casting import AssignmentTrait, Quest, QuestType, Trait
from larpmanager.models.event import ProgressStep, Run
from larpmanager.models.form import (
    QuestionApplicable,
    WritingAnswer,
    WritingChoice,
    WritingOption,
    WritingQuestion,
)
from larpmanager.models.miscellanea import PlayerRelationship
from larpmanager.models.registration import Registration
from larpmanager.models.writing import (
    Faction,
    Handout,
    HandoutTemplate,
    Plot,
    PlotCharacterRel,
    Prologue,
    PrologueType,
    SpeedLarp,
)
from larpmanager.utils.common import FileTypeValidator


class WritingForm(MyForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for s in ["cover"]:
            if s in self.fields and s not in self.params["features"]:
                del self.fields[s]

        if "assigned" in self.params["features"]:
            choices = [(m.id, m.show_nick()) for m in get_event_staffers(self.params["run"].event)]
            self.fields["assigned"].choices = [("", _("--- NOT ASSIGNED ---"))] + choices
        else:
            self.delete_field("assigned")

        if "progress" in self.params["features"]:
            self.fields["progress"].choices = [
                (el.id, str(el)) for el in ProgressStep.objects.filter(event=self.params["run"].event).order_by("order")
            ]
        else:
            self.delete_field("progress")

        # prepare translate text
        if "translate" in self.params["features"]:
            self.translate = {}
            for k in self.fields:
                if not isinstance(self.fields[k], CharField):
                    continue
                if k not in self.initial or not self.initial[k]:
                    continue
                self.translate[f"id_{k}"] = self.initial[k]

        self.show_link = ["id_teaser", "id_text"]


class PlayerRelationshipForm(MyForm):
    page_title = _("Character Relationship")

    class Meta:
        model = PlayerRelationship
        exclude = ["reg"]
        widgets = {
            "target": EventCharacterS2Widget,
        }
        labels = {"target": _("Character")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["target"].widget.set_event(self.params["run"].event)
        self.fields["target"].required = True

    def clean(self):
        cleaned_data = super().clean()

        if self.cleaned_data["target"].id == self.params["char"]["id"]:
            self.add_error("target", _("You cannot create a relationship towards yourself!"))

        try:
            rel = PlayerRelationship.objects.get(reg=self.params["run"].reg, target=self.cleaned_data["target"])
            if rel.id != self.instance.id:
                self.add_error("target", _("Already existing relationship!"))
        except ObjectDoesNotExist:
            pass

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if not instance.pk:
            instance.reg = self.params["run"].reg

        instance.save()

        return instance


class UploadElementsForm(forms.Form):
    elem = forms.FileField(
        validators=[
            FileTypeValidator(
                allowed_types=[
                    "application/csv",
                    "text/csv",
                    "text/plain",
                    "application/zip",
                    "text/html",
                ]
            )
        ]
    )


class BaseWritingForm(BaseRegistrationForm):
    gift = False
    answer_class = WritingAnswer
    choice_class = WritingChoice
    option_class = WritingOption
    question_class = WritingQuestion
    instance_key = "element_id"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # noinspection PyProtectedMember
        self.applicable = QuestionApplicable.get_applicable(self._meta.model._meta.model_name)

    def _init_questions(self, event):
        super()._init_questions(event)
        # noinspection PyProtectedMember
        self.questions = self.questions.filter(applicable=self.applicable)

    def get_options_query(self, event):
        query = super().get_options_query(event)
        return query.annotate(tickets_map=ArrayAgg("tickets"))

    def get_option_key_count(self, option):
        key = f"option_char_{option.id}"
        return key

    def save(self, commit=True):
        instance = super().save()

        instance.save()
        if hasattr(self, "questions"):
            orga = True
            if hasattr(self, "orga"):
                orga = self.orga
            self.save_reg_questions(instance, orga=orga)

        return instance


class PlotForm(WritingForm, BaseWritingForm):
    load_templates = ["plot"]

    load_js = ["characters-choices"]

    page_title = _("Plot")

    class Meta:
        model = Plot

        exclude = ("number", "temp", "hide")

        widgets = {
            "characters": EventCharacterS2WidgetMulti,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.init_orga_fields()
        self.reorder_field("characters")

        # PLOT CHARACTERS REL
        self.add_char_finder = []
        self.field_link = {}
        if self.instance.pk:
            for ch in (
                self.instance.get_plot_characters()
                .order_by("character__number")
                .values_list("character__id", "character__number", "character__name", "text")
            ):
                char = f"#{ch[1]} {ch[2]}"
                field = f"ch_{ch[0]}"
                id_field = f"id_{field}"
                self.fields[field] = forms.CharField(
                    widget=WritingTinyMCE(),
                    label=char,
                    help_text=_("This text will be added to the sheet of {name}".format(name=char)),
                    required=False,
                )

                self.initial[field] = ch[3]

                self.show_link.append(id_field)
                self.add_char_finder.append(id_field)
                reverse_args = [self.params["event"].slug, self.params["run"].number, ch[0]]
                self.field_link[id_field] = reverse("orga_characters_edit", args=reverse_args)

    def get_init_multi_character(self):
        que = PlotCharacterRel.objects.filter(plot__id=self.instance.pk)
        return que.values_list("character_id", flat=True)

    @staticmethod
    def save_multi_characters(instance, old, new):
        for ch in old - new:
            PlotCharacterRel.objects.filter(character_id=ch, plot_id=instance.pk).delete()
        for ch in new - old:
            PlotCharacterRel.objects.create(character_id=ch, plot_id=instance.pk)

    def save(self, commit=True):
        instance = super().save()

        if instance.pk:
            for pr in self.instance.get_plot_characters():
                field = f"ch_{pr.character_id}"
                if field not in self.cleaned_data:
                    continue
                if self.cleaned_data[field] == pr.text:
                    continue
                pr.text = self.cleaned_data[field]
                pr.save()

        return instance


class FactionForm(WritingForm, BaseWritingForm):
    load_templates = ["faction"]

    load_js = ["characters-choices"]

    page_title = _("Faction")

    class Meta:
        model = Faction

        exclude = ("number", "temp", "hide", "order")

        widgets = {
            "characters": EventCharacterS2WidgetMulti,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "user_character" not in self.params["features"]:
            self.delete_field("selectable")

        self.init_orga_fields()
        self.reorder_field("characters")


class QuestTypeForm(WritingForm):
    page_title = _("Quest type")

    class Meta:
        model = QuestType
        fields = ["progress", "name", "assigned", "teaser", "event"]

        widgets = {
            "teaser": WritingTinyMCE(),
            "text": WritingTinyMCE(),
        }


class QuestForm(WritingForm):
    page_title = _("Quest")

    class Meta:
        model = Quest
        fields = [
            "progress",
            "typ",
            "name",
            "assigned",
            "teaser",
            "text",
            "hide",
            "open_show",
            "event",
        ]

        widgets = {
            "teaser": WritingTinyMCE(),
            "text": WritingTinyMCE(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        que = self.params["run"].event.get_elements(QuestType)
        self.fields["typ"].choices = [(m.id, m.name) for m in que]

        # ~ #if not 'questbuilder_open' in self.params['features']:
        # ~ del self.fields['open_show']

        self.details = {}

        if not self.instance.pk:
            return

        # TRAITS CHARACTERS REL
        if Run.objects.filter(event=self.params["run"].event).aggregate(Max("number"))["number__max"] > 1:
            # do this only if this the only run of this event
            return

            # get traits
        txts = []
        for trait in self.instance.traits.all():
            char_name = "<" + _("NOT ASSIGNED") + ">"
            try:
                at = AssignmentTrait.objects.get(run=self.params["run"], trait=trait)
                reg = Registration.objects.get(run=self.params["run"], member=at.member, cancellation_date__isnull=True)
                chars = []
                for rcr in reg.rcrs.all():
                    chars.append(f"#{rcr.character.number}")
                char_name = ", ".join(chars)
            except ObjectDoesNotExist:
                print(traceback.format_exc())
                pass

            txts.append(f"{trait.name} - {char_name}")


class TraitForm(WritingForm):
    page_title = _("Trait")

    load_templates = ["trait"]

    class Meta:
        model = Trait
        fields = [
            "progress",
            "quest",
            "name",
            "assigned",
            "teaser",
            "text",
            "role",
            "keywords",
            "safety",
            "hide",
            "event",
        ]

        widgets = {
            "teaser": WritingTinyMCE(),
            "text": WritingTinyMCE(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        que = self.params["run"].event.get_elements(Quest)
        self.fields["quest"].choices = [(m.id, m.name) for m in que]


class HandoutForm(WritingForm):
    page_title = _("Handout")

    class Meta:
        model = Handout
        fields = ["progress", "template", "name", "assigned", "text", "event"]

        widgets = {
            "text": WritingTinyMCE(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        que = self.params["run"].event.get_elements(HandoutTemplate)
        self.fields["template"].choices = [(m.id, m.name) for m in que]


class HandoutTemplateForm(MyForm):
    load_templates = ["handout-template"]

    class Meta:
        model = HandoutTemplate
        exclude = ("number", "event")

        widgets = {"template": forms.FileInput(attrs={"accept": "application/vnd.oasis.opendocument.text"})}


class PrologueTypeForm(MyForm):
    class Meta:
        model = PrologueType
        fields = ["name"]


class PrologueForm(WritingForm):
    page_title = _("Prologue")

    load_js = ["characters-choices"]

    class Meta:
        model = Prologue

        exclude = ("teaser", "temp", "hide")

        widgets = {
            "characters": EventCharacterS2WidgetMulti,
            "text": WritingTinyMCE(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        que = self.params["run"].event.get_elements(PrologueType)
        self.fields["typ"].choices = [(m.id, m.name) for m in que]


class SpeedLarpForm(WritingForm):
    page_title = _("Speed larp")

    load_js = ["characters-choices"]

    class Meta:
        model = SpeedLarp
        exclude = ("teaser", "temp", "hide")

        widgets = {
            "characters": EventCharacterS2WidgetMulti,
            "text": WritingTinyMCE(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
