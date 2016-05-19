from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings
import aristotle_mdr.models as models
import aristotle_mdr.perms as perms
import aristotle_mdr.tests.utils as utils
from aristotle_mdr.utils import url_slugify_concept

from django.test.utils import setup_test_environment
setup_test_environment()


class ReviewRequestActionsPage(utils.LoggedInViewPages, TestCase):
    def setUp(self):
        super(ReviewRequestActionsPage, self).setUp()

        # There would be too many tests to test every item type against every other
        # But they all have identical logic, so one test should suffice
        self.item1 = models.ObjectClass.objects.create(name="Test Item 1 (visible to tested viewers)",definition=" ",workgroup=self.wg1)
        self.item2 = models.ObjectClass.objects.create(name="Test Item 2 (NOT visible to tested viewers)",definition=" ",workgroup=self.wg2)
        self.item3 = models.ObjectClass.objects.create(name="Test Item 3 (only visible to the editor)",definition=" ",workgroup=None,submitter=self.editor)

    def test_viewer_can_request_review(self):
        self.login_editor()

        response = self.client.get(reverse('aristotle:request_review',args=[self.item3.id]))
        self.assertEqual(response.status_code,403)

        response = self.client.get(reverse('aristotle:request_review',args=[self.item2.id]))
        self.assertEqual(response.status_code,403)

        response = self.client.get(reverse('aristotle:request_review',args=[self.item1.id]))
        self.assertEqual(response.status_code,200)
        form = response.context['form']

        self.assertEqual(self.item1.review_requests.count(),0)
        response = self.client.post(
            reverse('aristotle:request_review',args=[self.item1.id]),
            {
                'registration_authority': [str(self.ra.id)],
                'state': self.ra.public_state,
                'message': "Please review this",
            }
        )

        self.assertRedirects(response,url_slugify_concept(self.item1))
        self.assertEqual(self.item1.review_requests.count(),1)

    def test_registrar_has_valid_items_in_review(self):

        item1 = models.ObjectClass.objects.create(name="Test Item 1",definition=" ",workgroup=self.wg1)
        item2 = models.ObjectClass.objects.create(name="Test Item 2",definition=" ",workgroup=self.wg2)
        item3 = models.ObjectClass.objects.create(name="Test Item 3",definition=" ",workgroup=self.wg1)
        item4 = models.ObjectClass.objects.create(name="Test Item 4",definition=" ",workgroup=self.wg2)

        self.login_registrar()

        response = self.client.get(reverse('aristotle:userReadyForReview',))
        self.assertEqual(response.status_code,200)

        self.assertEqual(len(response.context['page']),0)

        review = models.ReviewRequest.objects.create(requester=self.su,registration_authority=self.ra)
        review.concepts.add(item1)
        review.concepts.add(item4)

        response = self.client.get(reverse('aristotle:userReadyForReview',))
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['page']),1)

        review = models.ReviewRequest.objects.create(requester=self.su,registration_authority=self.ra)
        review.concepts.add(item1)

        response = self.client.get(reverse('aristotle:userReadyForReview',))
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['page']),2)

        other_ra = models.RegistrationAuthority.objects.create(name="A different ra")
        review = models.ReviewRequest.objects.create(requester=self.su,registration_authority=other_ra)
        review.concepts.add(item2)

        response = self.client.get(reverse('aristotle:userReadyForReview',))
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['page']),2)

        other_ra.giveRoleToUser('registrar',self.registrar)
        response = self.client.get(reverse('aristotle:userReadyForReview',))
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['page']),3)

    def test_registrar_can_see_review(self):
        self.login_registrar()
        other_ra = models.RegistrationAuthority.objects.create(name="A different ra")

        review = models.ReviewRequest.objects.create(requester=self.editor,registration_authority=other_ra)
        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewDetails',args=[review.pk]))
        self.assertEqual(response.status_code,404)

        review = models.ReviewRequest.objects.create(requester=self.editor,registration_authority=self.ra)
        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewDetails',args=[review.pk]))
        self.assertEqual(response.status_code,200)

        review.status = models.REVIEW_STATES.cancelled
        review.save()

        response = self.client.get(reverse('aristotle:userReviewDetails',args=[review.pk]))
        self.assertEqual(response.status_code,404)

    def test_anon_cannot_see_review(self):
        self.logout()

        review = models.ReviewRequest.objects.create(requester=self.editor,registration_authority=self.ra)
        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewDetails',args=[review.pk]))
        self.assertEqual(response.status_code,302)
        # is redirected to login

    def test_editor_can_see_review(self):
        self.login_editor()

        review = models.ReviewRequest.objects.create(requester=self.editor,registration_authority=self.ra)
        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewDetails',args=[review.pk]))
        self.assertEqual(response.status_code,200)

        review.status = models.REVIEW_STATES.cancelled
        review.save()

        response = self.client.get(reverse('aristotle:userReviewDetails',args=[review.pk]))
        self.assertEqual(response.status_code,200)

    def test_registrar_can_accept_review(self):
        self.login_registrar()
        other_ra = models.RegistrationAuthority.objects.create(name="A different ra")

        review = models.ReviewRequest.objects.create(requester=self.editor,registration_authority=other_ra)
        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewAccept',args=[review.pk]))
        self.assertEqual(response.status_code,403)

        review = models.ReviewRequest.objects.create(requester=self.editor,registration_authority=self.ra)
        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewAccept',args=[review.pk]))
        self.assertEqual(response.status_code,200)

        review.status = models.REVIEW_STATES.cancelled
        review.save()

        review = models.ReviewRequest.objects.get(pk=review.pk) #decache
        response = self.client.get(reverse('aristotle:userReviewAccept',args=[review.pk]))
        self.assertEqual(response.status_code,403)
        
        response = self.client.post(reverse('aristotle:userReviewAccept',args=[review.pk]),
            {
                'response':"I can't accept this, its cancelled"
            })

        review = models.ReviewRequest.objects.get(pk=review.pk) #decache
        self.assertEqual(response.status_code,403)
        self.assertEqual(review.status, models.REVIEW_STATES.cancelled)
        self.assertTrue(bool(review.response) == False)

        review.status = models.REVIEW_STATES.submitted
        review.save()

        response = self.client.post(reverse('aristotle:userReviewAccept',args=[review.pk]),
            {
                'response':"I can accept this!",
                'registrationAuthorities':[other_ra.pk],
                'state':[models.STATES.standard],
                'cascadeRegistration':0, # no
            })
        self.assertTrue('registrationAuthorities' in response.context['form'].errors.keys())
        self.assertEqual(response.status_code,200)

        self.item1 = models.ObjectClass.objects.get(pk=self.item1.pk) # decache
        self.assertFalse(self.item1.is_public())

        response = self.client.post(reverse('aristotle:userReviewAccept',args=[review.pk]),
            {
                'response':"I can accept this!",
                'registrationAuthorities':[self.ra.pk],
                'state':[models.STATES.standard],
                'cascadeRegistration':0, # no
            })
        #self.assertEqual(response.status_code,200)
        self.assertRedirects(response,reverse('aristotle:userReadyForReview',))

        review = models.ReviewRequest.objects.get(pk=review.pk) #decache
        self.assertEqual(review.response, "I can accept this!")
        self.assertEqual(review.status,models.REVIEW_STATES.accepted)
        self.assertEqual(review.reviewer, self.registrar)

        self.item1 = models.ObjectClass.objects.get(pk=self.item1.pk) # decache
        self.assertTrue(self.item1.is_public())


    def test_registrar_can_reject_review(self):
        self.login_registrar()
        other_ra = models.RegistrationAuthority.objects.create(name="A different ra")

        review = models.ReviewRequest.objects.create(requester=self.editor,registration_authority=other_ra)
        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewReject',args=[review.pk]))
        self.assertEqual(response.status_code,403)

        review = models.ReviewRequest.objects.create(requester=self.editor,registration_authority=self.ra)
        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewReject',args=[review.pk]))
        self.assertEqual(response.status_code,200)

        review.status = models.REVIEW_STATES.cancelled
        review.save()

        review = models.ReviewRequest.objects.get(pk=review.pk) #decache
        response = self.client.get(reverse('aristotle:userReviewReject',args=[review.pk]))
        self.assertEqual(response.status_code,403)
        
        response = self.client.post(reverse('aristotle:userReviewReject',args=[review.pk]),
            {
                'response':"I can't reject this, its cancelled"
            })

        review = models.ReviewRequest.objects.get(pk=review.pk) #decache
        self.assertEqual(response.status_code,403)
        self.assertEqual(review.status, models.REVIEW_STATES.cancelled)
        self.assertTrue(bool(review.response) == False)

        review.status = models.REVIEW_STATES.submitted
        review.save()

        response = self.client.post(reverse('aristotle:userReviewReject',args=[review.pk]),
            {
                'response':"I can reject this!",
            })
        #self.assertEqual(response.status_code,200)
        self.assertRedirects(response,reverse('aristotle:userReadyForReview',))

        review = models.ReviewRequest.objects.get(pk=review.pk) #decache
        self.assertEqual(review.response, "I can reject this!")
        self.assertEqual(review.status,models.REVIEW_STATES.rejected)
        self.assertEqual(review.reviewer, self.registrar)

        self.item1 = models.ObjectClass.objects.get(pk=self.item1.pk) # decache
        self.assertFalse(self.item1.is_public())