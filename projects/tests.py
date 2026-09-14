from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Project, ProjectCategory, FeeType, ProjectFee, ProjectPhaseComment

class ProjectRestructuringTests(TestCase):
    def setUp(self):
        # Get or create categories
        self.category_power, _ = ProjectCategory.objects.get_or_create(name="POWER", defaults={"description": "Power projects"})
        self.category_const, _ = ProjectCategory.objects.get_or_create(name="Construction", defaults={"description": "Construction work"})
        
        # Get or create fee types
        self.fee_admin, _ = FeeType.objects.get_or_create(name="Admin Fee", defaults={"description": "Admin charges"})
        self.fee_vat, _ = FeeType.objects.get_or_create(name="VAT", defaults={"description": "Value Added Tax"})
        
        # Create user
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.staff_user = User.objects.create_user(username="staffuser", password="testpassword", is_staff=True)
        
        # Add staff_user to Level 3 and Level 4 group to satisfy permission checks
        from django.contrib.auth.models import Group
        level3_group, _ = Group.objects.get_or_create(name='Level 3')
        level4_group, _ = Group.objects.get_or_create(name='Level 4')
        self.staff_user.groups.add(level3_group, level4_group)

        # Create parent project
        self.parent_project = Project.objects.create(
            project_code="PRJ-PARENT",
            mda="Ministry of Power",
            project_name="Grid Expansion Project",
            location="Abuja",
            category=self.category_power,
            budget_amount=50000000.00
        )

    def test_project_creation_and_attributes(self):
        # Create child project linked to parent
        project = Project.objects.create(
            project_code="PRJ-001",
            year=2026,
            mda="Ministry of Works",
            project_name="Bridge Rehabilitation",
            location="Lagos",
            category=self.category_const,
            budget_amount=15000000.00,
            current_phase="POST_AWARD"
        )
        project.linked_projects.add(self.parent_project)
        
        self.assertEqual(project.category.name, "Construction")
        self.assertEqual(project.linked_projects.first().project_code, "PRJ-PARENT")
        self.assertEqual(project.year, 2026)
        self.assertEqual(project.current_phase, "POST_AWARD")
        self.assertEqual(project.get_current_phase_display(), "Post-Award Phase")

    def test_project_fees_relationship(self):
        # Create fees for the parent project
        fee1 = ProjectFee.objects.create(
            project=self.parent_project,
            fee_type=self.fee_admin,
            amount=250000.00
        )
        fee2 = ProjectFee.objects.create(
            project=self.parent_project,
            fee_type=self.fee_vat,
            amount=375000.00
        )
        
        self.assertEqual(self.parent_project.fees.count(), 2)
        fees_dict = {f.fee_type.name: f.amount for f in self.parent_project.fees.all()}
        self.assertEqual(fees_dict["Admin Fee"], 250000.00)
        self.assertEqual(fees_dict["VAT"], 375000.00)

    def test_project_form_and_views(self):
        self.client.login(username="staffuser", password="testpassword")
        
        # Test project creation via POST with fees formset
        url = reverse('projects:project_create')
        data = {
            'project_code': 'PRJ-NEW',
            'year': 2026,
            'mda': 'Ministry of Environment',
            'project_name': 'Erosion Control',
            'project_type': 'CONSTRUCTION',
            'execution_mode': 'SELF_EXECUTED',
            'location': 'Anambra',
            'category': self.category_const.pk,
            'parent_project': '',
            'part_name': '',
            'part_percentage': '100.00',
            'budget_amount': '8000000.00',
            'current_phase': 'PRE_AWARD',
            'execution_level_percentage': 0,
            'project_status': 'Initiated',
            'payment_status': 'Pending',
            'actual_contract_amount': '0.00',
            'in_house_benchmark': '0.00',
            'cost_percentage': '0.00',
            'mobilization_received': '0.00',
            'final_payment_received': '0.00',
            
            # Formset management fields
            'fees-TOTAL_FORMS': '1',
            'fees-INITIAL_FORMS': '0',
            'fees-MIN_NUM_FORMS': '0',
            'fees-MAX_NUM_FORMS': '1000',
            
            # Formset data fields
            'fees-0-fee_type': self.fee_admin.pk,
            'fees-0-amount': '150000.00',
            'fees-0-status': 'PENDING',
            'fees-0-id': '',
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302) # Redirects on success
        
        # Verify project and associated fee were created
        self.assertTrue(Project.objects.filter(project_code="PRJ-NEW").exists())
        new_project = Project.objects.get(project_code="PRJ-NEW")
        self.assertEqual(new_project.fees.count(), 1)
        self.assertEqual(new_project.fees.first().amount, 150000.00)

    def test_settings_page_access_denied_for_regular_user(self):
        self.client.login(username="testuser", password="testpassword")
        url = reverse('projects:settings')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302) # Redirected to dashboard

    def test_settings_page_access_allowed_for_staff(self):
        self.client.login(username="staffuser", password="testpassword")
        url = reverse('projects:settings')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200) # Access granted
        
    def test_settings_page_create_category(self):
        self.client.login(username="staffuser", password="testpassword")
        url = reverse('projects:settings')
        data = {
            'action': 'save_category',
            'name': 'Infrastructure',
            'description': 'Roads and rails'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ProjectCategory.objects.filter(name="Infrastructure").exists())

    def test_settings_page_delete_category_blocked_when_in_use(self):
        self.client.login(username="staffuser", password="testpassword")
        url = reverse('projects:settings')
        
        # Test parent_project is using self.category_power
        data = {
            'action': 'delete_category',
            'cat_id': self.category_power.pk
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        # Verify it was not deleted
        self.assertTrue(ProjectCategory.objects.filter(pk=self.category_power.pk).exists())
        
        # Verify message error was thrown
        # (We check that a message warning user is present)
        response_get = self.client.get(url)
        self.assertContains(response_get, "Cannot delete category")

    def test_project_split_parts_inheritance_and_rollups(self):
        # 1. Verify inheritance when saving a child project part
        child_part1 = Project.objects.create(
            parent_project=self.parent_project,
            project_name="Grid Expansion Part A",
            part_name="Part A",
            part_percentage=60.00,
            budget_amount=30000000.00,
            actual_contract_amount=35000000.00,
            mobilization_received=10000000.00,
            final_payment_received=0.00,
            execution_level_percentage=80
        )
        # Verify inherited fields
        self.assertEqual(child_part1.project_code, self.parent_project.project_code)
        self.assertEqual(child_part1.mda, self.parent_project.mda)
        self.assertEqual(child_part1.location, self.parent_project.location)
        self.assertEqual(child_part1.category, self.parent_project.category)

        # 2. Verify non-unique project code is allowed
        child_part2 = Project.objects.create(
            parent_project=self.parent_project,
            project_name="Grid Expansion Part B",
            part_name="Part B",
            part_percentage=40.00,
            budget_amount=20000000.00,
            actual_contract_amount=25000000.00,
            mobilization_received=5000000.00,
            final_payment_received=15000000.00,
            execution_level_percentage=30
        )
        self.assertEqual(child_part2.project_code, self.parent_project.project_code)

        # 3. Verify rollup values on the parent project
        self.assertTrue(self.parent_project.is_parent)
        self.assertEqual(self.parent_project.total_budget_amount, 50000000.00)
        self.assertEqual(self.parent_project.total_actual_contract_amount, 60000000.00)
        self.assertEqual(self.parent_project.total_mobilization_received, 15000000.00)
        self.assertEqual(self.parent_project.total_final_payment_received, 15000000.00)
        
        # 4. Verify weighted average execution level: (80% * 60 + 30% * 40) / 100 = (4800 + 1200) / 100 = 60%
        self.assertEqual(self.parent_project.average_execution_percentage, 60)

    def test_project_list_view_awarded_filter(self):
        self.client.login(username="staffuser", password="testpassword")

        # Create an awarded project with actual contract amount
        awarded_project = Project.objects.create(
            project_code="PRJ-AWARDED",
            mda="Ministry of Water",
            project_name="Dam Construction",
            location="Kano",
            category=self.category_const,
            budget_amount=20000000.00,
            actual_contract_amount=18000000.00,
            current_phase="POST_AWARD"
        )

        # Create a pre-award project
        pre_award_project = Project.objects.create(
            project_code="PRJ-PRE",
            mda="Ministry of Water",
            project_name="Feasibility Study",
            location="Kano",
            category=self.category_const,
            budget_amount=5000000.00,
            actual_contract_amount=0.00,
            current_phase="PRE_AWARD"
        )

        url = reverse('projects:project_list')

        # Test filtering for awarded projects
        response_awarded = self.client.get(url, {'awarded': 'awarded'})
        self.assertEqual(response_awarded.status_code, 200)
        projects_awarded = response_awarded.context['projects']
        self.assertIn(awarded_project, projects_awarded)
        self.assertNotIn(pre_award_project, projects_awarded)

        # Test filtering for pre-award projects
        response_pre = self.client.get(url, {'awarded': 'pre_award'})
        self.assertEqual(response_pre.status_code, 200)
        projects_pre = response_pre.context['projects']
        self.assertIn(pre_award_project, projects_pre)
        self.assertNotIn(awarded_project, projects_pre)

        # Test filtering by Category Name (e.g. POWER from dashboard click)
        response_cat = self.client.get(url, {'category': 'POWER'})
        self.assertEqual(response_cat.status_code, 200)
        projects_cat = response_cat.context['projects']
        self.assertIn(self.parent_project, projects_cat)
        self.assertNotIn(awarded_project, projects_cat)

        # Test combined category and MDA filter
        response_combined = self.client.get(url, {'category': 'Construction', 'mda': 'Ministry of Water'})
        self.assertEqual(response_combined.status_code, 200)
        projects_combined = response_combined.context['projects']
        self.assertIn(awarded_project, projects_combined)
        self.assertIn(pre_award_project, projects_combined)
        self.assertNotIn(self.parent_project, projects_combined)

    def test_mda_short_form_conversion_on_save(self):
        # Create project with long MDA string containing acronym in parentheses
        p = Project.objects.create(
            project_code="PRJ-NDE",
            mda="NATIONAL DIRECTORATE OF EMPLOYMENT (NDE)",
            project_name="Youth Training Program",
            location="Niger",
            category=self.category_const,
            budget_amount=10000000.00
        )
        p.refresh_from_db()
        # Verify the database column 'mda' itself contains the short form 'NDE'
        self.assertEqual(p.mda, "NDE")
        self.assertEqual(p.short_mda, "NDE")

    def test_project_list_view_staff_filter(self):
        self.client.login(username="staffuser", password="testpassword")

        # Create another staff user
        engineer = User.objects.create_user(
            username="engineer_jane", 
            first_name="Jane", 
            last_name="Doe", 
            password="testpassword"
        )

        # Project assigned to staff_user
        proj_staff = Project.objects.create(
            project_code="PRJ-ASSIGNED-1",
            mda="Ministry of Works",
            project_name="Highway Expansion",
            location="Lagos",
            category=self.category_const,
            staff_assigned=self.staff_user,
            budget_amount=10000000.00
        )

        # Project assigned to engineer
        proj_engineer = Project.objects.create(
            project_code="PRJ-ASSIGNED-2",
            mda="Ministry of Power",
            project_name="Solar Grid",
            location="Kaduna",
            category=self.category_power,
            staff_assigned=engineer,
            budget_amount=20000000.00
        )

        # Project with no assigned staff
        proj_unassigned = Project.objects.create(
            project_code="PRJ-UNASSIGNED",
            mda="Ministry of Water",
            project_name="Water Treatment Facility",
            location="Enugu",
            category=self.category_const,
            staff_assigned=None,
            budget_amount=15000000.00
        )

        url = reverse('projects:project_list')

        # 1. Filter by staff user ID
        response_staff = self.client.get(url, {'staff': self.staff_user.id})
        self.assertEqual(response_staff.status_code, 200)
        projects_staff = response_staff.context['projects']
        self.assertIn(proj_staff, projects_staff)
        self.assertNotIn(proj_engineer, projects_staff)
        self.assertNotIn(proj_unassigned, projects_staff)

        # 2. Filter by staff username or name
        response_name = self.client.get(url, {'staff': 'engineer_jane'})
        self.assertEqual(response_name.status_code, 200)
        projects_name = response_name.context['projects']
        self.assertIn(proj_engineer, projects_name)
        self.assertNotIn(proj_staff, projects_name)
        self.assertNotIn(proj_unassigned, projects_name)

        # 3. Filter for unassigned projects
        response_unassigned = self.client.get(url, {'staff': 'unassigned'})
        self.assertEqual(response_unassigned.status_code, 200)
        projects_unassigned = response_unassigned.context['projects']
        self.assertIn(proj_unassigned, projects_unassigned)
        self.assertIn(self.parent_project, projects_unassigned) # parent_project in setUp has staff_assigned=None
        self.assertNotIn(proj_staff, projects_unassigned)
        self.assertNotIn(proj_engineer, projects_unassigned)

    def test_project_phase_comments(self):
        self.client.login(username="staffuser", password="testpassword")

        # 1. Post a comment to PRE_AWARD phase
        url = reverse('projects:add_phase_comment', kwargs={'project_pk': self.parent_project.pk})
        response = self.client.post(url, {
            'phase': 'PRE_AWARD',
            'comment': 'Tender journal purchased successfully.'
        })
        self.assertEqual(response.status_code, 302)

        # Verify ProjectPhaseComment creation
        pre_comments = self.parent_project.pre_award_phase_comments
        self.assertEqual(pre_comments.count(), 1)
        self.assertEqual(pre_comments.first().comment, 'Tender journal purchased successfully.')
        self.assertEqual(pre_comments.first().author, self.staff_user)

        # 2. Post a comment to POST_AWARD phase
        self.client.post(url, {
            'phase': 'POST_AWARD',
            'comment': 'Award letter received from agency.'
        })
        post_comments = self.parent_project.post_award_phase_comments
        self.assertEqual(post_comments.count(), 1)
        self.assertEqual(post_comments.first().comment, 'Award letter received from agency.')

        # 3. Post a comment to EXECUTION phase
        self.client.post(url, {
            'phase': 'EXECUTION',
            'comment': 'Site handed over to sub-contractor.'
        })
        exec_comments = self.parent_project.execution_phase_comments
        self.assertEqual(exec_comments.count(), 1)
        self.assertEqual(exec_comments.first().comment, 'Site handed over to sub-contractor.')

        # 4. Check Detail View rendering
        detail_url = reverse('projects:project_detail', kwargs={'pk': self.parent_project.pk})
        detail_resp = self.client.get(detail_url)
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, 'Tender journal purchased successfully.')
        self.assertContains(detail_resp, 'Award letter received from agency.')
        self.assertContains(detail_resp, 'Site handed over to sub-contractor.')

        # 5. Check ProjectActivityLog entry
        activity_log = self.parent_project.activity_logs.filter(action_type='PHASE_COMMENT').first()
        self.assertIsNotNone(activity_log)
        self.assertEqual(activity_log.user, self.staff_user)





