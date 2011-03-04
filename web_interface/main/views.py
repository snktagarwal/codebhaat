from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from main.models import *
from settings import MEDIA_URL, MAX_SUBMISSIONS
from django.contrib.auth.models import User
from django.template import RequestContext
from django.contrib.auth.decorators import login_required

def home(request):
    return render_to_response('main/index.html',context_instance=RequestContext(request))

def credits(request):
    return render_to_response('main/credits.html',context_instance=RequestContext(request))

def contests(request):
    contests = Contest.objects.all()    
    return render_to_response('main/contest_list.html', {'contests':contests}, context_instance=RequestContext(request))

@login_required
def problem_list(request, contest_pk):
    problem_list = []
    context = {}
    if not request.user.is_active:
        request.user = testuser
    
    user = request.user    
    if contest_pk:
        contest = get_object_or_404(Contest, pk=contest_pk)        
        if request.user.is_superuser:
            problems = contest.problem_set.all()
        else:
            problems = contest.problem_set.filter(is_public=True)
        context['contest'] = contest

    tag = request.GET.get('tag', False)
        
    if tag:
        problems = problems.filter(tags__name=tag)        
            
    for problem in problems:
        problem.status_img = problem.status_image(user)            
        problem_list.append(problem)

    if request.user.is_superuser:
        submissions = Submission.objects.filter(is_latest=True, problem__contests__pk=contest.pk).order_by('-time')[:10] 
    else:
        submissions = Submission.objects.filter(is_latest=True, problem__contests__pk=contest.pk, problem__is_public=True).order_by('-time')[:5]

    rank=Rank.objects.get_or_create(user=user, contest=contest)[0]
    
    return render_to_response('main/problem_list.html', {
        'problems': problem_list,
        'submissions':submissions,        
        'rank': rank,
    },context_instance=RequestContext(request, context))

@login_required
def problem_detail(request, problem_pk, contest_pk=None):
    if contest_pk:
        contest = get_object_or_404(Contest, pk=contest_pk)
    else:
        contest = None
    if request.user.is_superuser:
        problem = get_object_or_404(Problem, pk=problem_pk)
    else:
        problem = get_object_or_404(Problem, pk=problem_pk, is_public=True)    
    public_testcases = problem.testcase_set.filter(is_public=True)
    user = request.user
    last_submission = []
    last_submission_ready = False
    user_submissions = Submission.objects.filter(user=user,
                                                 problem=problem).order_by('-time')
    if user_submissions:
        last_submission  = user_submissions[0]
        last_submission_ready = last_submission.ready()
        
        
    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)
        #Saving the form if it is valid
        if form.is_valid():
            new_submission = form.save(commit=False)
            #Calling the worker to perform the task submit through celery
            new_submission.save(user=user, problem=problem, contest=contest)
            #Redirect to the results of the submission
            return HttpResponseRedirect(problem.get_absolute_url(contest))
    else:
        #New form for a submission                
        form = SubmissionForm()    
    
    left_submissions = MAX_SUBMISSIONS - last_submission.attempts()  if last_submission else MAX_SUBMISSIONS
    submission_limit_reached = left_submissions <= 0
    
    rank=Rank.objects.get_or_create(user=user, contest=contest)[0]
    
    return render_to_response('main/problem_detail.html', {
        'problem': problem,
        'public_testcases':public_testcases,
        'form': form,
        'left_submissions':left_submissions,
        'rank': rank,
        'submission_limit_reached':submission_limit_reached,        
        'media_prefix':MEDIA_URL,
        'last_submission':last_submission,
        'last_submission_ready':last_submission_ready,
        'contest':contest},
        context_instance=RequestContext(request))
   
@login_required
def problem_input(request, problem_pk, testcase_id):
    testcase = get_object_or_404(TestCase, pk=testcase_id)
    if testcase.is_public:
        return HttpResponse(testcase.input_file.read(),mimetype="text/in")
    else:
        raise Http404

@login_required
def problem_output(request, problem_pk, testcase_id):
    testcase = get_object_or_404(TestCase, pk=testcase_id)
    if testcase.is_public:
        return HttpResponse(testcase.output_file.read(),mimetype="text/out")
    else:
        raise Http404
       
       
def reg_team(request, team_id, team_name, password, email):
    if request.GET.get('pass', False) == "paswrd":
        user = User(username=team_id, first_name=team_name)
        user.set_password(password)
        user.save()
        user.email = email
        user.save()
        return HttpResponse()        
    else:
        raise Http404  
    
